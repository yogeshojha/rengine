from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select

from shared.definitions.intensity import TransportTool
from shared.enums.scan import Phase, StageGroup, StageRole
from shared.enums.target import TargetType
from shared.enums.task_status import TaskStatus
from shared.logging import get_logger
from shared.models.bgp_summary import TargetBgpSummary
from shared.models.dns import DnsLookup
from shared.models.target import Target
from shared.models.whois import WhoisRecord
from shared.utils.datetime import utc_now
from shared.utils.validation import normalize_domain
from stages.base import Stage, StageResult
from stages.target_enrichment.config import TargetEnrichmentConfig
from tools.dnsx.service import DnsxService
from tools.whois.service import WhoisNotApplicableError, WhoisService

logger = get_logger(__name__)

_STALE = timedelta(days=7)
_DNS_TYPES = {TargetType.DOMAIN.value, TargetType.URL.value}


def _is_stale(queried_at: datetime | None) -> bool:
    if queried_at is None:
        return True
    return (utc_now() - queried_at) > _STALE


class TargetEnrichmentStage(Stage):
    name = "target_enrichment"
    title = "Target Enrichment"
    description = "Resolve the target and attach DNS, WHOIS and BGP context."
    phase = Phase.DISCOVERY.value
    group = StageGroup.HOSTS.value
    role = StageRole.SUPPORT.value
    tools = ("dnsx", "whois")
    transport_tool = TransportTool.DNSX.value
    touches_target = False
    config_model = TargetEnrichmentConfig
    _notes: list[str]

    def run(self) -> StageResult:
        self._check_abort()
        target = self.session.get(Target, self.ctx.target_id)
        if target is None:
            return StageResult(counts={})

        self._notes = []
        dns_records = self._ensure_dns(target)
        whois_present = self._ensure_whois(target)
        bgp_present = self._read_bgp()

        self.emit_progress(
            f"{dns_records} DNS records, "
            f"WHOIS {'stored' if whois_present else 'absent'}, "
            f"BGP {'stored' if bgp_present else 'absent'}"
        )
        return StageResult(
            counts={
                "dns_records": dns_records,
                "whois": int(whois_present),
                "bgp": int(bgp_present),
            },
            warnings=self._notes,
            partial=bool(self._notes),
        )

    def _ensure_dns(self, target: Target) -> int:
        if self.ctx.target_type not in _DNS_TYPES:
            return 0
        lookup = (
            self.session.get(DnsLookup, target.dns_lookup_id)
            if target.dns_lookup_id
            else None
        )
        if lookup is None or _is_stale(lookup.queried_at):
            host = normalize_domain(self.ctx.target_value)
            try:
                lookup = DnsxService(
                    timeout=max(120, self.transport.timeout),
                    threads=self.transport.threads,
                    query_timeout=self.transport.timeout,
                    **self.wiring("dnsx"),
                ).lookup_and_store(self.session, target.id, host)
                target.dns_lookup_id = lookup.id
                target.dns_status = TaskStatus.SUCCESS
                self.session.add(target)
                self.session.commit()
            except Exception as exc:
                logger.warning("in-scan DNS refresh failed for %s: %s", host, exc)
                self._notes.append(f"DNS was not refreshed for {host}. {exc}")
        return len(lookup.records) if lookup else 0

    def _ensure_whois(self, target: Target) -> bool:
        record = (
            self.session.get(WhoisRecord, target.whois_record_id)
            if target.whois_record_id
            else None
        )
        if record is None or _is_stale(record.queried_at):
            svc = WhoisService(proxy_url=self.ctx.resolved.proxy_url)
            ttype = TargetType(self.ctx.target_type)
            try:
                response = svc.do_lookup(
                    svc.lookup_key(self.ctx.target_value, ttype), ttype
                )
                record = svc.store_record_sync(self.session, response)
                target.whois_record_id = record.id
                target.whois_status = TaskStatus.SUCCESS
                target.whois_error = None
                self.session.add(target)
                self.session.commit()
            except WhoisNotApplicableError as exc:
                target.whois_status = TaskStatus.NOT_APPLICABLE
                target.whois_error = str(exc)[:1000]
                self.session.add(target)
                self.session.commit()
            except Exception as exc:
                logger.warning("in-scan WHOIS refresh failed: %s", exc)
                self._notes.append(f"WHOIS was not refreshed. {exc}")
        return record is not None

    def _read_bgp(self) -> bool:
        bgp = self.session.execute(
            select(TargetBgpSummary).where(
                TargetBgpSummary.target_id == self.ctx.target_id
            )
        ).scalar_one_or_none()
        return bgp is not None
