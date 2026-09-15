from __future__ import annotations

import time
from collections import Counter

from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from shared.definitions.domain_posture import MAX_ZONES_PER_SCAN
from shared.definitions.domains import registrable_domain
from shared.definitions.intensity import TransportTool
from shared.enums.scan import AssetKind, Intensity, Phase, StageGroup, StageRole
from shared.enums.target import TargetType
from shared.logging import get_logger
from shared.models.subdomain import Subdomain
from shared.services.domain_posture import (
    evaluate,
    fold_onto_hosts,
    gather,
    replace_rows,
    row_for,
)
from shared.utils.text import counted
from shared.utils.validation import normalize_domain
from stages.base import Stage, StageResult
from stages.dns_posture.config import DnsPostureConfig
from stages.dns_posture.lookup import DnsxLookup
from tools.dnsx.client import DnsxClient, DnsxError

logger = get_logger(__name__)

_RUN_TIMEOUT = 600
_FOLD_ATTEMPTS = 3
_FOLD_RETRY_SECONDS = 2
_MIN_THREADS = 10
_NAMED_ZONES = 5


class DnsPostureStage(Stage):
    name = "dns_posture"
    title = "Domain posture"
    description = "SPF, DMARC, DKIM, MTA-STS, DNSSEC and CAA read from each zone."
    phase = Phase.DEPTH.value
    depends_on = frozenset({"subdomain_discovery"})
    group = StageGroup.HOSTS.value
    role = StageRole.SUPPORT.value
    consumes = frozenset({AssetKind.HOSTS.value})
    applies_to = frozenset({TargetType.DOMAIN.value, TargetType.URL.value})
    tools = ("dnsx",)
    transport_tool = TransportTool.DNSX.value
    touches_target = True
    passive_capable = True
    config_model = DnsPostureConfig

    def run(self) -> StageResult:
        self._check_abort()
        hosts_per_zone = self._zones()
        if not hosts_per_zone:
            return StageResult(counts={"zones": 0})
        try:
            client = DnsxClient(
                timeout=_RUN_TIMEOUT,
                threads=max(self.transport.threads, _MIN_THREADS),
                query_timeout=self.transport.timeout,
                recorder=self.ctx.recorder,
                extra_args=self.ctx.resolved.tool_args("dnsx"),
            )
        except DnsxError as exc:
            return StageResult(warnings=[str(exc)], partial=True)

        passive = self.ctx.resolved.intensity == Intensity.PASSIVE.value
        lookup = DnsxLookup(client, self.net_options())
        records = gather(
            hosts_per_zone,
            lookup,
            selectors=self.cfg.dkim_selectors,
            fetch_policy=not passive,
            on_progress=self.emit_progress,
            should_stop=self._aborted,
            workers=self.transport.threads,
        )
        self._check_abort()

        rows = []
        unanswered: list[str] = []
        failing = 0
        for zone, rec in records.items():
            if not rec.answered:
                unanswered.append(zone)
                continue
            posture = evaluate(rec)
            failing += len(posture.issues)
            rows.append(
                row_for(
                    scan_id=self.ctx.scan_id,
                    target_id=self.ctx.target_id,
                    project_id=self.ctx.project_id,
                    rec=rec,
                    posture=posture,
                    hosts=hosts_per_zone[zone],
                )
            )
        stored = replace_rows(self.session, self.ctx.scan_id, rows)
        self.session.commit()
        self._fold()

        warnings: list[str] = []
        if unanswered:
            named = ", ".join(unanswered[:_NAMED_ZONES])
            warnings.append(
                f"{counted(len(unanswered), 'zone')} did not answer: {named}."
            )
        self.emit_progress(
            f"{counted(stored, 'zone')} checked, {counted(failing, 'check')} failing"
        )
        return StageResult(
            counts={"zones": stored, "posture_issues": failing},
            warnings=warnings,
            partial=bool(unanswered),
        )

    def _fold(self) -> None:
        for attempt in range(_FOLD_ATTEMPTS):
            try:
                fold_onto_hosts(self.session, self.ctx.scan_id)
                self.session.commit()
                return
            except OperationalError:
                self.session.rollback()
                logger.warning("posture fold retried", attempt=attempt + 1)
                time.sleep(_FOLD_RETRY_SECONDS)
        logger.warning("posture fold left to finalize", scan_id=str(self.ctx.scan_id))

    def _aborted(self) -> bool:
        return self.ctx.is_aborted is not None and self.ctx.is_aborted()

    def _zones(self) -> dict[str, int]:
        """Registrable domains in the scan, with the hosts each one carries."""
        names = self.session.scalars(
            select(Subdomain.name).where(
                Subdomain.scan_id == self.ctx.scan_id,
                Subdomain.is_excluded.is_(False),
            )
        ).all()
        counts: Counter[str] = Counter()
        for name in names:
            zone = registrable_domain(name)
            if zone:
                counts[zone] += 1
        apex = normalize_domain(self.ctx.target_value)
        if apex and registrable_domain(f"_.{apex}") == apex:
            counts.setdefault(apex, 0)
        ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        return dict(ranked[:MAX_ZONES_PER_SCAN])
