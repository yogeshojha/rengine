from __future__ import annotations

import time
from collections import Counter

from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from shared.definitions.domain_posture import (
    MAIL_PREFIXES,
    MAX_MAIL_HOSTS_PER_SCAN,
    MAX_ZONES_PER_SCAN,
    MX_BATCH_SIZE,
    MX_SWEEP_CAP,
)
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
from shared.services.domain_posture.records import NULL_MX, mx_host
from shared.services.domain_posture.write import zone_of
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


def _exchanges(record: dict[str, list[str]]) -> set[str]:
    return {mx_host(v) for v in record.get("mx", [])}


def _mail_rank(name: str) -> tuple[int, int, str]:
    """Mail-named and short names first."""
    head = name.split(".", 1)[0]
    named = 0 if any(head.startswith(p) for p in MAIL_PREFIXES) else 1
    return (named, name.count("."), name)


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
    _silent_mx: list[str]
    _active: set[str]

    def run(self) -> StageResult:
        self._check_abort()
        names = self._names()
        zones = self._zones(names)
        if not zones:
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
        parents: dict[str, str | None] = dict.fromkeys(zones)
        self._silent_mx = []
        mail_hosts, not_asked = self._mail_hosts(lookup, names, zones)
        for host in mail_hosts:
            parents[host] = zone_of(host, zones)
        self._check_abort()
        hosts_per_zone = self._hosts_per_zone(names, parents)
        records = gather(
            parents,
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
        if not_asked:
            warnings.append(
                f"{counted(len(not_asked), 'name')} not checked for a mail host of "
                "their own."
            )
        if self._silent_mx:
            warnings.append(
                f"{counted(len(self._silent_mx), 'name')} gave no MX answer and may "
                "hold one."
            )
        self.emit_progress(
            f"{counted(stored, 'zone')} checked, {counted(failing, 'check')} failing"
        )
        return StageResult(
            counts={"zones": stored, "posture_issues": failing},
            warnings=warnings,
            partial=bool(unanswered or not_asked or self._silent_mx),
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

    def _names(self) -> list[str]:
        rows = self.session.execute(
            select(Subdomain.name, Subdomain.is_active).where(
                Subdomain.scan_id == self.ctx.scan_id,
                Subdomain.is_excluded.is_(False),
            )
        ).all()
        self._active = {name for name, active in rows if active}
        return [name for name, _ in rows]

    def _zones(self, names: list[str]) -> list[str]:
        """Registrable domains in the scan, most hosts first."""
        counts: Counter[str] = Counter()
        for name in names:
            zone = registrable_domain(name)
            if zone:
                counts[zone] += 1
        apex = normalize_domain(self.ctx.target_value)
        if apex and registrable_domain(f"_.{apex}") == apex:
            counts.setdefault(apex, 0)
        ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        return [zone for zone, _ in ranked[:MAX_ZONES_PER_SCAN]]

    def _mail_hosts(
        self, lookup: DnsxLookup, names: list[str], zones: list[str]
    ) -> tuple[list[str], list[str]]:
        """Names below a zone with exchanges of their own, and the names not asked."""
        zone_set = set(zones)
        candidates = sorted(
            (n for n in names if n not in zone_set and zone_of(n, zones)),
            key=_mail_rank,
        )
        asked, skipped = candidates[:MX_SWEEP_CAP], candidates[MX_SWEEP_CAP:]
        if not asked:
            return [], skipped
        self.emit_progress(f"asking {len(asked)} names for MX records")
        zone_mx = {
            zone: _exchanges(rec)
            for zone, rec in lookup.records(zones, ("mx",)).items()
        }
        found: list[str] = []
        for start in range(0, len(asked), MX_BATCH_SIZE):
            self._check_abort()
            batch = asked[start : start + MX_BATCH_SIZE]
            answers = lookup.records(batch, ("mx", "a"))
            silent = [n for n in batch if n not in answers and n in self._active]
            if silent:
                answers.update(lookup.records(silent, ("mx", "a")))
            for name in batch:
                if name not in answers:
                    if name in self._active:
                        self._silent_mx.append(name)
                    continue
                exchanges = _exchanges(answers[name])
                if not exchanges or exchanges == {NULL_MX}:
                    continue
                if exchanges == zone_mx.get(zone_of(name, zones) or "", set()):
                    continue
                found.append(name)
        kept, over = found[:MAX_MAIL_HOSTS_PER_SCAN], found[MAX_MAIL_HOSTS_PER_SCAN:]
        return kept, skipped + over

    @staticmethod
    def _hosts_per_zone(
        names: list[str], parents: dict[str, str | None]
    ) -> dict[str, int]:
        counts: Counter[str] = Counter()
        for name in names:
            zone = zone_of(name, parents)
            if zone is not None:
                counts[zone] += 1
        return {zone: counts.get(zone, 0) for zone in parents}
