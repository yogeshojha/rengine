from __future__ import annotations

from sqlalchemy import select

from shared.enums.scan import Phase
from shared.enums.target import TargetType
from shared.logging import get_logger
from shared.models.bgp_summary import TargetBgpSummary
from shared.models.ip_address import IpAddress
from shared.models.ripestat import RIPEStatASOverview
from shared.models.target import Target
from shared.models.whois import WhoisRecord
from stages.base import IP_TARGETS, Stage, StageResult
from stages.ip_enrichment.config import IpEnrichmentConfig

logger = get_logger(__name__)



def _parse_asn(value: str) -> int | None:
    try:
        return int(value.upper().replace("AS", "").strip())
    except ValueError:
        return None


class IpEnrichmentStage(Stage):
    name = "ip_enrichment"
    title = "IP Enrichment"
    description = "Attach ASN, prefix and WHOIS context to discovered IPs."
    phase = Phase.DISCOVERY.value
    level = 1
    applies_to = IP_TARGETS
    touches_target = False
    config_model = IpEnrichmentConfig

    def run(self) -> StageResult:
        self._check_abort()
        rows = list(
            self.session.execute(
                select(IpAddress).where(IpAddress.scan_id == self.ctx.scan_id)
            )
            .scalars()
            .all()
        )
        if not rows:
            return StageResult(counts={"enriched": 0})

        asn, org, country = self._target_context()
        enriched = 0
        for row in rows:
            changed = False
            if asn is not None and row.asn is None:
                row.asn = asn
                changed = True
            if org and not row.asn_org:
                row.asn_org = org[:255]
                changed = True
            if country and not row.country:
                row.country = country[:10]
                changed = True
            if changed:
                self.session.add(row)
                enriched += 1
        self.session.commit()
        self.emit_progress(f"enriched {enriched} IP assets (ASN/org)")
        return StageResult(counts={"enriched": enriched})

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
