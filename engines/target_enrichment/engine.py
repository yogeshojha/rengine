from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select

from engines.base import Engine, EngineResult
from engines.target_enrichment.config import TargetEnrichmentConfig
from shared.enums.target import TargetType
from shared.enums.task_status import TaskStatus
from shared.logging import get_logger
from shared.models.bgp_summary import TargetBgpSummary
from shared.models.dns import DnsLookup
from shared.models.target import Target
from shared.models.whois import WhoisRecord
from shared.utils.datetime import utc_now
from shared.utils.validation import normalize_domain, normalize_query
from tools.dnsx.service import DnsxService
from tools.whois.service import WhoisService

logger = get_logger(__name__)

_STALE = timedelta(days=7)
_DNS_TYPES = {TargetType.DOMAIN.value, TargetType.URL.value}


def _is_stale(queried_at: datetime | None) -> bool:
    if queried_at is None:
        return True
    return (utc_now() - queried_at) > _STALE


class TargetEnrichmentEngine(Engine):
    name = "target_enrichment"

    def should_run(self) -> bool:
        return True

    def run(self) -> EngineResult:
        self._check_abort()
        cfg = TargetEnrichmentConfig.from_resolved(self.ctx.resolved)
        target = self.session.get(Target, self.ctx.target_id)
        if target is None:
            return EngineResult(counts={})

        dns_records = self._ensure_dns(target, cfg)
        whois_present = self._ensure_whois(target)
        bgp_present = self._read_bgp()

        self.emit_progress(
            f"enrichment — dns:{dns_records} "
            f"whois:{int(whois_present)} bgp:{int(bgp_present)}"
        )
        return EngineResult(
            counts={
                "dns_records": dns_records,
                "whois": int(whois_present),
                "bgp": int(bgp_present),
            }
        )

    def _ensure_dns(self, target: Target, cfg: TargetEnrichmentConfig) -> int:
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
                    timeout=max(120, cfg.dns_timeout), threads=cfg.dns_threads
                ).lookup_and_store(self.session, target.id, host)
                target.dns_lookup_id = lookup.id
                target.dns_status = TaskStatus.SUCCESS
                self.session.add(target)
                self.session.commit()
            except Exception as exc:
                logger.warning("in-scan DNS refresh failed for %s: %s", host, exc)
        return len(lookup.records) if lookup else 0

    def _ensure_whois(self, target: Target) -> bool:
        record = (
            self.session.get(WhoisRecord, target.whois_record_id)
            if target.whois_record_id
            else None
        )
        if record is None or _is_stale(record.queried_at):
            try:
                ttype = TargetType(self.ctx.target_type)
                normalized = normalize_query(self.ctx.target_value, ttype)
                svc = WhoisService()
                response = svc.do_lookup(normalized, ttype)
                record = svc.store_record_sync(self.session, response)
                target.whois_record_id = record.id
                target.whois_status = TaskStatus.SUCCESS
                self.session.add(target)
                self.session.commit()
            except Exception as exc:
                logger.warning("in-scan WHOIS refresh failed: %s", exc)
        return record is not None

    def _read_bgp(self) -> bool:
        bgp = self.session.execute(
            select(TargetBgpSummary).where(
                TargetBgpSummary.target_id == self.ctx.target_id
            )
        ).scalar_one_or_none()
        return bgp is not None
