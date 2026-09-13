from __future__ import annotations

from sqlalchemy import select, text, update

from shared.definitions.surface import SurfaceDimension
from shared.enums.scan import Phase, StageGroup, StageRole
from shared.enums.target import TargetType
from shared.logging import get_logger
from shared.models.ip_address import IpAddress
from shared.models.ripestat import RIPEStatASOverview
from shared.services.ip_asn import enrich_addresses, ranges_ready, sync_ranges
from shared.services.ip_inventory import collect_ips, materialize
from stages.base import ALL_TARGETS, Stage, StageResult, parse_asn
from stages.ip_enrichment.config import IpEnrichmentConfig

logger = get_logger(__name__)

_ADOPT_CDN_SQL = """
UPDATE ip_addresses a
SET is_cdn = true, cdn_name = coalesce(a.cdn_name, h.cdn_name)
FROM (
    SELECT ip, max(cdn_name) AS cdn_name FROM http_assets
    WHERE scan_id = :sid AND ip IS NOT NULL AND is_cdn IS TRUE
    GROUP BY ip
) h
WHERE a.scan_id = :sid AND a.ip = h.ip AND a.is_cdn IS NOT TRUE
"""

_BACKFILL_ASSETS_SQL = """
UPDATE http_assets h SET asn = a.asn, asn_org = a.asn_org
FROM ip_addresses a
WHERE a.scan_id = :sid AND h.scan_id = :sid AND h.ip = a.ip AND a.asn IS NOT NULL
"""

_BACKFILL_SUBDOMAINS_SQL = """
UPDATE subdomains s SET asn = a.asn, asn_org = a.asn_org
FROM ip_addresses a
WHERE a.scan_id = :sid AND s.scan_id = :sid
  AND cast(s.resolved_ips AS jsonb) ->> 0 = a.ip
  AND a.asn IS NOT NULL
"""

_ADOPT_HOST_CDN_SQL = """
UPDATE subdomains s
SET is_cdn = true, cdn_name = coalesce(s.cdn_name, h.cdn_name)
FROM (
    SELECT s2.id, max(a.cdn_name) AS cdn_name
    FROM subdomains s2
    CROSS JOIN LATERAL jsonb_array_elements_text(cast(s2.resolved_ips AS jsonb)) AS elem(ip)
    JOIN ip_addresses a ON a.scan_id = s2.scan_id AND a.ip = elem.ip
    WHERE s2.scan_id = :sid AND a.is_cdn IS TRUE AND s2.is_cdn IS NOT TRUE
    GROUP BY s2.id
) h
WHERE s.id = h.id
"""


class IpEnrichmentStage(Stage):
    name = "ip_enrichment"
    title = "IP Enrichment"
    description = (
        "Resolve ASN, network operator and country for every IP address the scan found."
    )
    phase = Phase.DEPTH.value
    depends_on = frozenset(
        {
            "origin_probe",
            "passive_ports",
            "reverse_dns",
            "service_fingerprint",
        }
    )
    group = StageGroup.ADDRESSES.value
    role = StageRole.SUPPORT.value
    applies_to = ALL_TARGETS
    touches_target = False
    always_on = True
    config_model = IpEnrichmentConfig

    def run(self) -> StageResult:
        self._check_abort()
        found = self._collect()
        if not found:
            return StageResult(counts={"ips": 0, "enriched": 0})

        created = self._materialize(found)
        self._check_abort()
        ready = self._ensure_ranges()
        enriched = self._enrich()
        self._backfill()
        self.session.commit()
        self.publish_results(SurfaceDimension.IPS.value)
        self.emit_progress(
            f"{enriched} of {len(found)} addresses resolved to an ASN or country"
        )
        warnings = (
            []
            if ready
            else [
                f"IP-to-ASN ranges are still loading. {len(found):,} addresses "
                "were stored without a network or country."
            ]
        )
        return StageResult(
            counts={"ips": len(found), "new": created, "enriched": enriched},
            warnings=warnings,
            partial=not ready,
        )

    def _collect(self) -> list[str]:
        return collect_ips(self.session, self.ctx.scan_id)

    def _materialize(self, ips: list[str]) -> int:
        return materialize(
            self.session,
            scan_id=self.ctx.scan_id,
            target_id=self.ctx.target_id,
            project_id=self.ctx.project_id,
            ips=ips,
        )

    def _ensure_ranges(self) -> bool:
        """False when another loader holds the lock."""
        if ranges_ready(self.session):
            return True
        logger.info("ip range tables empty, syncing before enrichment")
        self.emit_progress("Downloading IP address ranges")
        sync_ranges(self.session)
        return ranges_ready(self.session)

    def _enrich(self) -> int:
        """Most addresses were enriched as they were written."""
        enrich_addresses(self.session, scan_id=self.ctx.scan_id)
        self._apply_target_asn()
        return int(
            self.session.execute(
                text(
                    "SELECT count(*) FROM ip_addresses "
                    "WHERE scan_id = :sid AND (asn IS NOT NULL OR country IS NOT NULL)"
                ).bindparams(sid=self.ctx.scan_id)
            ).scalar()
            or 0
        )

    def _backfill(self) -> None:
        for statement in (
            _ADOPT_CDN_SQL,
            _ADOPT_HOST_CDN_SQL,
            _BACKFILL_ASSETS_SQL,
            _BACKFILL_SUBDOMAINS_SQL,
        ):
            self.session.execute(text(statement).bindparams(sid=self.ctx.scan_id))

    def _apply_target_asn(self) -> None:
        """An ASN target states the network of its own sweep."""
        if self.ctx.target_type != TargetType.ASN.value:
            return
        asn = parse_asn(self.ctx.target_value)
        if asn is None:
            return
        overview = self.session.execute(
            select(RIPEStatASOverview).where(RIPEStatASOverview.asn == asn)
        ).scalar_one_or_none()
        org = (overview.holder or "")[:255] if overview else None
        self.session.execute(
            update(IpAddress)
            .where(IpAddress.scan_id == self.ctx.scan_id, IpAddress.asn.is_(None))
            .values(asn=asn, asn_org=org)
        )
