from __future__ import annotations

from sqlalchemy import select, text

from shared.enums.scan import Phase, StageGroup, StageRole
from shared.enums.target import TargetType
from shared.logging import get_logger
from shared.models.bgp_summary import TargetBgpSummary
from shared.models.ip_address import IpAddress
from shared.models.ripestat import RIPEStatASOverview
from shared.models.target import Target
from shared.models.whois import WhoisRecord
from shared.services.ip_asn import ranges_ready, sync_ranges
from shared.services.ip_inventory import collect_ips, materialize
from stages.base import ALL_TARGETS, Stage, StageResult
from stages.ip_enrichment.config import IpEnrichmentConfig

logger = get_logger(__name__)

_ENRICH_SQL = """
UPDATE ip_addresses a SET
    asn     = coalesce(r.asn, a.asn),
    asn_org = coalesce(r.as_name, a.asn_org),
    country = coalesce(c.country, a.country)
FROM ip_addresses base
LEFT JOIN LATERAL (
    SELECT asn, as_name, end_ip FROM ip_asn_ranges
    WHERE start_ip <= base.ip::inet ORDER BY start_ip DESC LIMIT 1
) r ON r.end_ip >= base.ip::inet
LEFT JOIN LATERAL (
    SELECT country, end_ip FROM ip_country_ranges
    WHERE start_ip <= base.ip::inet ORDER BY start_ip DESC LIMIT 1
) c ON c.end_ip >= base.ip::inet
WHERE a.id = base.id AND base.scan_id = :sid
"""

# http probing is the authority on CDN; fold it back so ip_addresses is the full record
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


def _parse_asn(value: str) -> int | None:
    try:
        return int(value.upper().replace("AS", "").strip())
    except ValueError:
        return None


class IpEnrichmentStage(Stage):
    name = "ip_enrichment"
    title = "IP Enrichment"
    description = "Resolve ASN, network operator and country for every IP address."
    phase = Phase.DEPTH.value
    level = 0
    group = StageGroup.ADDRESSES.value
    role = StageRole.SUPPORT.value
    applies_to = ALL_TARGETS
    touches_target = False
    config_model = IpEnrichmentConfig

    def run(self) -> StageResult:
        self._check_abort()
        found = self._collect()
        if not found:
            return StageResult(counts={"ips": 0, "enriched": 0})

        created = self._materialize(found)
        self._check_abort()
        self._ensure_ranges()
        enriched = self._enrich()
        self._backfill()
        self.session.commit()
        self.emit_progress(
            f"{enriched} of {len(found)} addresses resolved to an ASN or country"
        )
        return StageResult(
            counts={"ips": len(found), "new": created, "enriched": enriched}
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

    def _ensure_ranges(self) -> None:
        if ranges_ready(self.session):
            return
        logger.info("ip range tables empty, syncing before enrichment")
        self.emit_progress("Downloading IP address ranges")
        sync_ranges(self.session)

    def _enrich(self) -> int:
        self.session.execute(text(_ENRICH_SQL).bindparams(sid=self.ctx.scan_id))
        self._apply_target_context()
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
        self.session.execute(text(_ADOPT_CDN_SQL).bindparams(sid=self.ctx.scan_id))
        self.session.execute(
            text(_BACKFILL_ASSETS_SQL).bindparams(sid=self.ctx.scan_id)
        )
        self.session.execute(
            text(_BACKFILL_SUBDOMAINS_SQL).bindparams(sid=self.ctx.scan_id)
        )

    def _apply_target_context(self) -> None:
        """Last-resort fill from the target's own ASN/WHOIS for anything still blank."""
        asn, org, country = self._target_context()
        if asn is None and not org and not country:
            return
        rows = (
            self.session.execute(
                select(IpAddress).where(
                    IpAddress.scan_id == self.ctx.scan_id,
                )
            )
            .scalars()
            .all()
        )
        for row in rows:
            if asn is not None and row.asn is None:
                row.asn = asn
            if org and not row.asn_org:
                row.asn_org = org[:255]
            if country and not row.country:
                row.country = country[:10]

    def _target_context(self) -> tuple[int | None, str | None, str | None]:
        asn: int | None = None
        org: str | None = None
        country: str | None = None

        if self.ctx.target_type == TargetType.ASN.value:
            asn = _parse_asn(self.ctx.target_value)
            if asn is not None:
                overview = self.session.execute(
                    select(RIPEStatASOverview).where(RIPEStatASOverview.asn == asn)
                ).scalar_one_or_none()
                if overview:
                    org = overview.holder
        else:
            bgp = self.session.execute(
                select(TargetBgpSummary).where(
                    TargetBgpSummary.target_id == self.ctx.target_id
                )
            ).scalar_one_or_none()
            if bgp:
                asn = bgp.asn
                org = bgp.holder

        target = self.session.get(Target, self.ctx.target_id)
        if target is not None and target.whois_record_id:
            whois = self.session.get(WhoisRecord, target.whois_record_id)
            if whois and whois.country:
                country = whois.country
        return asn, org, country
