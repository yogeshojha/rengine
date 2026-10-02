from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, date, datetime, time, timedelta
from itertools import pairwise
from uuid import UUID

from sqlalchemy import (
    Text,
    and_,
    case,
    cast,
    exists,
    func,
    not_,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import scan_deltas as stored_deltas
from app.services.dashboard import DashboardService
from app.services.scan import ScanService
from app.services.target_estate import TargetEstateService
from app.services.target_scope import Targets
from shared.definitions.dashboard import (
    CERT_BUCKETS,
    CHANGES_LIMIT,
    DISCOVERY_LIMIT,
    EXPIRED_CERT_QUERY,
    EXPIRING_CERT_QUERY,
    EXPIRING_DAYS,
    EXPOSURE_TOP,
    ITEMS_CAP,
    QUEUE_LIMIT,
    RUNS_PER_TARGET,
    SERIES_DAYS,
    STALE_DAYS,
    TIER_ACT_EPSS,
    TIER_ATTEND_EPSS,
    TIER_ORDER,
    QueueTier,
    cert_bucket_query,
    window_key,
    window_since,
)
from shared.definitions.estate import EstateTriageState
from shared.definitions.evidence import EVIDENCE_ORDER, Evidence
from shared.definitions.ports import (
    SENSITIVE_PORTS,
    SERVICE_CLASS_LABELS,
    ServiceClass,
    service_label,
)
from shared.definitions.surface import SURFACE_LABELS, SURFACE_ORDER, SurfaceDimension
from shared.definitions.threat_intel import EXPLOITED_SIGNALS
from shared.definitions.vulnerabilities import (
    ACTIONABLE_SEVERITIES,
    SEVERITY_LABELS,
    SEVERITY_ORDER,
    SUPPRESSED_STATES,
    Severity,
    coerce_severity,
)
from shared.enums.scan import SCAN_OPEN_STATUSES, ScanActivityStatus, ScanStatus
from shared.enums.scan_schedule import ScheduleStatus
from shared.models.dashboard import (
    DashboardCertBucket,
    DashboardCerts,
    DashboardCertSignal,
    DashboardChangeRow,
    DashboardDay,
    DashboardDiscoveredDomain,
    DashboardDiscovery,
    DashboardDiscoverySource,
    DashboardEvidenceCell,
    DashboardExposedService,
    DashboardExposure,
    DashboardExposureBand,
    DashboardFinding,
    DashboardOverview,
    DashboardRisk,
    DashboardSurfaceMetric,
    DashboardTargetCount,
    DashboardTargetRow,
    ExpiringTarget,
    StaleTarget,
)
from shared.models.ip_address import IpAddress
from shared.models.port import Port
from shared.models.scan import Scan
from shared.models.scan_activity import ScanActivity
from shared.models.scan_schedule import ScanSchedule
from shared.models.subdomain import Subdomain
from shared.models.target import Target
from shared.models.threat_intel import IntelSignal
from shared.models.vulnerability import (
    SeverityCount,
    Vulnerability,
    VulnerabilityTriage,
)
from shared.models.whois import WhoisRecord
from shared.services import scan_deltas
from shared.services.asset_query.predicates import (
    answered,
    cert_state,
    live,
    vuln_corroborated_ids,
    vuln_seen_earlier,
)
from shared.services.asset_query.tokens import token
from shared.services.scan_scope import census_only, covering_stages, covers
from shared.utils.datetime import utc_now

WEB = SurfaceDimension.WEB_ASSETS.value
SERVICES = SurfaceDimension.SERVICES.value
IPS = SurfaceDimension.IPS.value
VULNS = SurfaceDimension.VULNERABILITIES.value

_TABLES = scan_deltas.TABLES
_TERMINAL_BAD = (ScanStatus.FAILED.value, ScanStatus.CANCELLED.value)

Counts = dict[str, dict[UUID, tuple[int, datetime]]]
Covered = dict[str, dict[UUID, list[UUID]]]


def _started(scan: Scan) -> datetime:
    return scan.started_at or scan.created_at


def _suppressed():
    return exists(
        select(1).where(
            VulnerabilityTriage.target_id == Vulnerability.target_id,
            VulnerabilityTriage.fingerprint == Vulnerability.fingerprint,
            VulnerabilityTriage.state.in_(SUPPRESSED_STATES),
        )
    )


def _severity_rank():
    return case(
        {name: index for index, name in enumerate(SEVERITY_ORDER)},
        value=Vulnerability.severity,
        else_=len(SEVERITY_ORDER),
    )


def _act():
    return or_(
        Vulnerability.is_kev.is_(True),
        Vulnerability.kev_ransomware.is_(True),
        Vulnerability.evidence == Evidence.PROVEN.value,
        func.coalesce(Vulnerability.epss_score, 0) >= TIER_ACT_EPSS,
        Vulnerability.severity == Severity.CRITICAL.value,
    )


def _attend():
    return or_(
        Vulnerability.severity.in_((Severity.HIGH.value, Severity.MEDIUM.value)),
        func.coalesce(Vulnerability.epss_score, 0) >= TIER_ATTEND_EPSS,
    )


def _tier_of(row: Vulnerability) -> str:
    if (
        row.is_kev
        or row.kev_ransomware
        or row.evidence == Evidence.PROVEN.value
        or (row.epss_score or 0) >= TIER_ACT_EPSS
        or row.severity == Severity.CRITICAL.value
    ):
        return QueueTier.ACT.value
    if (
        row.severity in (Severity.HIGH.value, Severity.MEDIUM.value)
        or (row.epss_score or 0) >= TIER_ATTEND_EPSS
    ):
        return QueueTier.ATTEND.value
    return QueueTier.TRACK.value


class DashboardOverviewService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.signals = DashboardService(session)
        self.scans = ScanService(session)

    async def overview(
        self, project_id: UUID, window: str, targets: Targets = None
    ) -> DashboardOverview:
        window = window_key(window)
        now = utc_now()
        cutoff = window_since(window, now)
        series_cutoff = datetime.combine(
            (now - timedelta(days=SERIES_DAYS)).date(), time.min, tzinfo=UTC
        )

        scoped = targets
        targets, expires = await self._targets(project_id, scoped)
        runs_by_target, runs_total = await self._runs(project_id, series_cutoff, scoped)
        scans: dict[UUID, Scan] = {
            s.id: s for runs in runs_by_target.values() for s in runs
        }
        counts = await self._counts(scans)
        ran = await self._ran(list(scans))
        vuln_covered = await self._vuln_covered(list(scans))
        covered = self._covered(runs_by_target, counts, ran, vuln_covered)
        baselines = self._baselines(counts, scans)
        firsts, severity_firsts = await self._first_seen(scans, baselines)
        names = {t.id: t.target_value for t in targets}

        signals = await self.signals.signals(project_id, scoped)
        out = DashboardOverview(
            generated_at=now,
            window=window,
            since=cutoff,
            signals=signals,
            runs_total=runs_total,
            certs=DashboardCerts(
                expired=DashboardCertSignal(query=EXPIRED_CERT_QUERY),
                expiring=DashboardCertSignal(query=EXPIRING_CERT_QUERY),
            ),
        )
        out.targets_total = len(targets)
        out.first_run = scoped is None and not targets and not runs_total
        out.targets_scanned = sum(1 for t in targets if runs_by_target.get(t.id))

        in_window = [s for s in scans.values() if _started(s) >= cutoff]
        out.runs_in_window = len(in_window)
        out.outcomes_in_window = dict(Counter(s.status for s in in_window))
        out.failed_in_window = out.outcomes_in_window.get(ScanStatus.FAILED.value, 0)

        latest_cover = {
            key: {tid: ids[0] for tid, ids in per_target.items() if ids}
            for key, per_target in covered.items()
        }
        out.surface = self._surface(counts, latest_cover)
        addresses = await self._addresses(list(latest_cover[IPS].values()))
        for metric in out.surface:
            if metric.key == IPS:
                metric.value = addresses
        out.answering_hosts = await self._answering(list(latest_cover[WEB].values()))

        risk_ids = list(latest_cover[VULNS].values())
        out.risk = await self._risk(risk_ids, firsts, baselines, in_window, cutoff)

        service_ids = list(latest_cover[SERVICES].values())
        out.exposure = await self._exposure(service_ids, scans, names)
        await self._certs(out.certs, list(latest_cover[WEB].values()), now)

        monitored = await self._monitored(project_id)
        out.targets_monitored = sum(1 for t in targets if t.id in monitored)

        self._items(out, targets, runs_by_target, expires, now)
        out.changes = await self._changes(
            in_window, counts, firsts, baselines, names, targets
        )
        retired = await self._retired(covered, scans, series_cutoff)
        out.retired_in_window = {
            key: sum(retired[key].get(s.id, 0) for s in in_window)
            for key in SURFACE_ORDER
        }
        out.daily = self._daily(
            scans,
            firsts,
            baselines,
            series_cutoff,
            now,
            covered,
            counts,
            retired,
            severity_firsts,
        )
        out.targets = [
            DashboardTargetRow(
                id=t.id, value=t.target_value, monitored=t.id in monitored
            )
            for t in targets
        ]
        return out

    async def discovery(self, project_id: UUID) -> DashboardDiscovery:
        """Registrable domains the estate names that are not targets."""
        estate = await TargetEstateService(self.session).for_project(project_id)
        out = DashboardDiscovery()
        candidates = [
            d for d in estate.domains if d.state == EstateTriageState.OPEN.value
        ]
        for d in candidates[:DISCOVERY_LIMIT]:
            out.domains.append(
                DashboardDiscoveredDomain(
                    domain=d.domain,
                    hostname_count=sum(s.count for s in d.signals),
                    sources=[
                        DashboardDiscoverySource(
                            target_id=src.target_id,
                            target_value=src.target_value,
                        )
                        for src in d.sources
                    ],
                )
            )
        return out

    def _items(
        self,
        out: DashboardOverview,
        targets: list[Target],
        runs_by_target: dict[UUID, list[Scan]],
        expires: dict[UUID, datetime | None],
        now: datetime,
    ) -> None:
        """The item lists behind the attention tiles."""
        stale_before = now - timedelta(days=STALE_DAYS)
        for t in targets:
            runs = runs_by_target.get(t.id)
            if not runs:
                out.targets_never_scanned += 1
            elif _started(runs[0]) < stale_before:
                out.stale.append(_stale_row(t, _started(runs[0])))
        out.stale.sort(key=lambda x: x.last_scanned_at or now)
        out.targets_stale = len(out.stale)
        out.stale = out.stale[:ITEMS_CAP]
        expiring_after = now + timedelta(days=EXPIRING_DAYS)
        out.expiring = sorted(
            (
                ExpiringTarget(
                    target_id=t.id, target_value=t.target_value, expires_at=at
                )
                for t in targets
                if (at := expires.get(t.id)) and at <= expiring_after
            ),
            key=lambda x: x.expires_at,
        )[:ITEMS_CAP]

    async def _targets(
        self, project_id: UUID, scoped: Targets = None
    ) -> tuple[list[Target], dict[UUID, datetime | None]]:
        query = (
            select(Target, WhoisRecord.expiration_date)
            .join(WhoisRecord, WhoisRecord.id == Target.whois_record_id, isouter=True)
            .where(Target.project_id == project_id)
            .order_by(Target.target_value.asc())
        )
        if scoped is not None:
            query = query.where(Target.id.in_(scoped))
        result = await self.session.execute(query)
        targets = []
        expires: dict[UUID, datetime | None] = {}
        for target, expires_at in result.all():
            targets.append(target)
            expires[target.id] = expires_at
        return targets, expires

    async def _runs(
        self, project_id: UUID, series_cutoff: datetime, scoped: Targets = None
    ) -> tuple[dict[UUID, list[Scan]], int]:
        """The latest runs per target plus everything inside the series window."""
        in_scope = [Scan.project_id == project_id, census_only()]
        if scoped is not None:
            in_scope.append(Scan.target_id.in_(scoped))
        ordering = func.coalesce(Scan.started_at, Scan.created_at)
        rn = (
            func.row_number()
            .over(
                partition_by=Scan.target_id,
                order_by=[ordering.desc(), Scan.created_at.desc()],
            )
            .label("rn")
        )
        ranked = (
            select(Scan.id.label("id"), rn, ordering.label("at"))
            .where(*in_scope)
            .subquery()
        )
        result = await self.session.execute(
            select(Scan)
            .join(ranked, ranked.c.id == Scan.id)
            .where((ranked.c.rn <= RUNS_PER_TARGET) | (ranked.c.at >= series_cutoff))
            .order_by(ordering.desc(), Scan.created_at.desc())
        )
        by_target: dict[UUID, list[Scan]] = defaultdict(list)
        for scan in result.scalars().all():
            by_target[scan.target_id].append(scan)
        total = await self.session.scalar(
            select(func.count()).select_from(Scan).where(*in_scope)
        )
        return by_target, int(total or 0)

    async def _counts(self, scans: dict[UUID, Scan]) -> Counts:
        """Rows per scan and when its first row landed, per dimension."""
        out: Counts = {key: {} for key in _TABLES}
        scan_ids = list(scans)
        if not scan_ids:
            return out
        live = [sid for sid in scan_ids if scans[sid].status in SCAN_OPEN_STATUSES]
        for key, model in _TABLES.items():
            if key in scan_deltas.FIRST_SEEN:
                out[key] = await stored_deltas.row_counts(
                    self.session, key, scan_ids, live
                )
                continue
            result = await self.session.execute(
                select(model.scan_id, func.count(), func.min(model.discovered_at))
                .where(model.scan_id.in_(scan_ids), not_(_suppressed()))
                .group_by(model.scan_id)
            )
            out[key] = {row[0]: (int(row[1]), row[2]) for row in result.all()}
        return out

    async def _ran(self, scan_ids: list[UUID]) -> dict[UUID, set[str]]:
        if not scan_ids:
            return {}
        result = await self.session.execute(
            select(ScanActivity.scan_id, ScanActivity.name).where(
                ScanActivity.scan_id.in_(scan_ids),
                ScanActivity.status == ScanActivityStatus.SUCCESS.value,
            )
        )
        ran: dict[UUID, set[str]] = defaultdict(set)
        for scan_id, name in result.all():
            ran[scan_id].add(name)
        return ran

    async def _vuln_covered(self, scan_ids: list[UUID]) -> set[UUID]:
        if not scan_ids:
            return set()
        result = await self.session.execute(
            select(Scan.id).where(
                Scan.id.in_(scan_ids),
                covers(Vulnerability, SurfaceDimension.VULNERABILITIES.value),
            )
        )
        return set(result.scalars())

    def _covered(
        self,
        runs_by_target: dict[UUID, list[Scan]],
        counts: Counts,
        ran: dict[UUID, set[str]],
        vuln_covered: set[UUID],
    ) -> Covered:
        """Per dimension and target, the scans that ran it, newest first."""
        vuln = SurfaceDimension.VULNERABILITIES.value
        by_dimension = covering_stages()
        out: Covered = {key: {} for key in SURFACE_ORDER}
        for tid, runs in runs_by_target.items():
            for key, names in by_dimension.items():
                out[key][tid] = [
                    r.id
                    for r in runs
                    if (
                        r.id in vuln_covered
                        if key == vuln
                        else (ran.get(r.id, set()) & names) or r.id in counts[key]
                    )
                ]
        return out

    async def _first_seen(
        self, scans: dict[UUID, Scan], baselines: dict[str, set[UUID]]
    ) -> tuple[dict[str, dict[UUID, int]], dict[UUID, dict[str, int]]]:
        """Per dimension, how many keys each scan was the first to report for its target."""
        out: dict[str, dict[UUID, int]] = {key: {} for key in _TABLES}
        by_severity: dict[UUID, dict[str, int]] = {}
        for key in _TABLES:
            sids = [sid for sid in baselines.get(key, ()) if sid in scans]
            if not sids:
                continue
            if key in scan_deltas.FIRST_SEEN:
                live = [sid for sid in sids if scans[sid].status in SCAN_OPEN_STATUSES]
                counted = await stored_deltas.first_seen(self.session, key, sids, live)
            else:
                by_severity = await self._first_seen_findings(sids)
                counted = {sid: sum(per.values()) for sid, per in by_severity.items()}
            out[key] = {sid: counted.get(sid, 0) for sid in sids}
        return out, by_severity

    async def _first_seen_findings(
        self, sids: list[UUID]
    ) -> dict[UUID, dict[str, int]]:
        """Findings each scan was the first to report by severity, triaged-away ones excluded."""
        rows = await self.session.execute(
            select(Vulnerability.scan_id, Vulnerability.severity, func.count())
            .where(
                Vulnerability.scan_id.in_(sids),
                not_(scan_deltas.seen_earlier(VULNS)),
                not_(_suppressed()),
            )
            .group_by(Vulnerability.scan_id, Vulnerability.severity)
        )
        out: dict[UUID, dict[str, int]] = defaultdict(dict)
        for sid, severity, n in rows.all():
            key = coerce_severity(severity)
            out[sid][key] = out[sid].get(key, 0) + int(n)
        return out

    def _baselines(
        self, counts: Counts, scans: dict[UUID, Scan]
    ) -> dict[str, set[UUID]]:
        """Scans with an earlier scan of the same target holding rows of the dimension."""
        out: dict[str, set[UUID]] = {}
        for key, per_scan in counts.items():
            by_target: dict[UUID, list[tuple[datetime, UUID]]] = defaultdict(list)
            for sid, (_, first_at) in per_scan.items():
                scan = scans.get(sid)
                if scan is not None:
                    by_target[scan.target_id].append((first_at, sid))
            with_baseline: set[UUID] = set()
            for entries in by_target.values():
                entries.sort()
                earliest = entries[0][0]
                with_baseline.update(sid for at, sid in entries if at > earliest)
            out[key] = with_baseline
        return out

    def _surface(
        self,
        counts: Counts,
        latest_cover: dict[str, dict[UUID, UUID]],
    ) -> list[DashboardSurfaceMetric]:
        return [
            DashboardSurfaceMetric(
                key=key,
                label=SURFACE_LABELS[key],
                value=sum(
                    counts[key].get(sid, (0, None))[0]
                    for sid in latest_cover[key].values()
                ),
            )
            for key in SURFACE_ORDER
        ]

    async def _risk(
        self,
        risk_ids: list[UUID],
        firsts: dict[str, dict[UUID, int]],
        baselines: dict[str, set[UUID]],
        in_window: list[Scan],
        since: datetime,
    ) -> DashboardRisk:
        risk = DashboardRisk(targets_scanned=len(risk_ids))
        risk.new_in_window = sum(
            firsts[VULNS].get(s.id, 0) for s in in_window if s.id in baselines[VULNS]
        )
        if not risk_ids:
            return risk
        live_rows = Vulnerability.scan_id.in_(risk_ids)
        rows = await self.session.execute(
            select(Vulnerability.severity, func.count())
            .where(live_rows, not_(_suppressed()))
            .group_by(Vulnerability.severity)
        )
        tally: dict[str, int] = defaultdict(int)
        for severity, count in rows.all():
            tally[coerce_severity(severity)] += count
        risk.total = sum(tally.values())
        risk.actionable = sum(tally[s] for s in ACTIONABLE_SEVERITIES)
        risk.by_severity = [
            SeverityCount(severity=s, label=SEVERITY_LABELS[s], count=tally.get(s, 0))
            for s in SEVERITY_ORDER
            if tally.get(s, 0) > 0 or s != Severity.UNKNOWN.value
        ]
        risk.kev = int(
            await self.session.scalar(
                select(func.count())
                .select_from(Vulnerability)
                .where(live_rows, Vulnerability.is_kev.is_(True), not_(_suppressed()))
            )
            or 0
        )
        risk.ransomware = int(
            await self.session.scalar(
                select(func.count())
                .select_from(Vulnerability)
                .where(
                    live_rows,
                    Vulnerability.kev_ransomware.is_(True),
                    not_(_suppressed()),
                )
            )
            or 0
        )
        risk.overdue = int(
            await self.session.scalar(
                select(func.count())
                .select_from(Vulnerability)
                .where(
                    live_rows,
                    Vulnerability.kev_due_date.isnot(None),
                    Vulnerability.kev_due_date < func.current_date(),
                    not_(_suppressed()),
                )
            )
            or 0
        )
        risk.newly_exploited = int(
            await self.session.scalar(
                select(func.count(func.distinct(IntelSignal.vulnerability_id)))
                .select_from(IntelSignal)
                .join(Vulnerability, Vulnerability.id == IntelSignal.vulnerability_id)
                .where(
                    IntelSignal.scan_id.in_(risk_ids),
                    IntelSignal.kind.in_(EXPLOITED_SIGNALS),
                    IntelSignal.created_at >= since,
                    not_(_suppressed()),
                )
            )
            or 0
        )
        risk.suppressed = int(
            await self.session.scalar(
                select(func.count())
                .select_from(Vulnerability)
                .where(live_rows, _suppressed())
            )
            or 0
        )
        risk.targets_affected = int(
            await self.session.scalar(
                select(func.count(func.distinct(Vulnerability.target_id))).where(
                    live_rows, not_(_suppressed())
                )
            )
            or 0
        )
        rung = case(
            (
                Vulnerability.evidence == Evidence.PROVEN.value,
                Evidence.PROVEN.value,
            ),
            (
                Vulnerability.id.in_(vuln_corroborated_ids(risk_ids)),
                Evidence.CORROBORATED.value,
            ),
            else_=Vulnerability.evidence,
        )
        cells = await self.session.execute(
            select(Vulnerability.severity, rung, func.count())
            .where(live_rows, not_(_suppressed()))
            .group_by(Vulnerability.severity, rung)
        )
        matrix: dict[tuple[str, str], int] = defaultdict(int)
        for severity, evidence, n in cells.all():
            matrix[(coerce_severity(severity), evidence)] += int(n)
        risk.evidence = [
            DashboardEvidenceCell(severity=sev, evidence=ev, count=matrix[(sev, ev)])
            for sev in SEVERITY_ORDER
            for ev in EVIDENCE_ORDER
            if matrix.get((sev, ev))
        ]
        tiers = (
            await self.session.execute(
                select(
                    func.count().filter(_act()),
                    func.count().filter(and_(not_(_act()), _attend())),
                    func.count().filter(and_(not_(_act()), not_(_attend()))),
                ).where(live_rows, not_(_suppressed()))
            )
        ).one()
        risk.tiers = {
            tier: int(n or 0) for tier, n in zip(TIER_ORDER, tiers, strict=True)
        }
        risk.queue = await self._queue(risk_ids, baselines)
        return risk

    async def _queue(
        self, risk_ids: list[UUID], baselines: dict[str, set[UUID]]
    ) -> list[DashboardFinding]:
        live_rows = Vulnerability.scan_id.in_(risk_ids)
        spread = (
            select(
                Vulnerability.target_id.label("target_id"),
                Vulnerability.template_id.label("template_id"),
                func.count(
                    func.distinct(
                        func.coalesce(Vulnerability.host, Vulnerability.matched_at)
                    )
                ).label("hosts"),
                func.min(_severity_rank()).label("rank"),
                func.min(Vulnerability.id.cast(Text)).label("sample"),
                func.count()
                .filter(Vulnerability.replayed_from_id.isnot(None))
                .label("replays"),
            )
            .where(live_rows, not_(_suppressed()))
            .group_by(Vulnerability.target_id, Vulnerability.template_id)
            .subquery()
        )
        rows = await self.session.execute(
            select(Vulnerability, spread.c.hosts, Target.target_value, spread.c.replays)
            .join(
                spread, Vulnerability.id == cast(spread.c.sample, Vulnerability.id.type)
            )
            .join(Target, Target.id == Vulnerability.target_id)
            .order_by(
                spread.c.rank.asc(),
                Vulnerability.is_kev.desc(),
                Vulnerability.epss_score.desc().nulls_last(),
                Vulnerability.cvss_score.desc().nulls_last(),
                spread.c.hosts.desc(),
                Vulnerability.discovered_at.desc(),
            )
            .limit(QUEUE_LIMIT)
        )
        items = list(rows.all())
        if not items:
            return []
        seen_ids = {
            row[0]
            for row in (
                await self.session.execute(
                    select(Vulnerability.id).where(
                        Vulnerability.id.in_([row[0].id for row in items]),
                        vuln_seen_earlier(),
                    )
                )
            ).all()
        }
        out = []
        for row, hosts, target_value, replays in items:
            out.append(
                DashboardFinding(
                    id=row.id,
                    scan_id=row.scan_id,
                    target_id=row.target_id,
                    target_value=target_value,
                    template_id=row.template_id,
                    name=row.template_name,
                    severity=row.severity,
                    host=row.host,
                    matched_at=row.matched_at,
                    host_count=int(hosts or 1),
                    is_kev=row.is_kev,
                    is_new=row.scan_id in baselines[VULNS] and row.id not in seen_ids,
                    cve_ids=list(row.cve_ids or []),
                    epss_score=row.epss_score,
                    cvss_score=row.cvss_score,
                    discovered_at=row.discovered_at,
                    evidence=row.evidence,
                    tier=_tier_of(row),
                    replays=int(replays or 0),
                )
            )
        return out

    async def _exposure(
        self, service_ids: list[UUID], scans: dict[UUID, Scan], names: dict[UUID, str]
    ) -> DashboardExposure:
        """What is listening across every target's latest service scan."""
        out = DashboardExposure(targets=len(service_ids))
        if not service_ids:
            return out
        scope = Port.scan_id.in_(service_ids)
        sensitive = Port.number.in_(SENSITIVE_PORTS)
        n = func.count()
        totals = (
            await self.session.execute(
                select(
                    n,
                    func.count(func.distinct(Port.ip)),
                    n.filter(sensitive),
                    func.count(func.distinct(Port.scan_id)).filter(sensitive),
                ).where(scope)
            )
        ).one()
        (
            out.services,
            out.addresses,
            out.sensitive,
            out.sensitive_targets,
        ) = (int(v or 0) for v in totals)

        band_rows = (
            await self.session.execute(
                select(Port.service_class, n, func.count(func.distinct(Port.scan_id)))
                .where(scope)
                .group_by(Port.service_class)
            )
        ).all()
        by_class = {str(k): (int(c), int(t)) for k, c, t in band_rows}
        out.bands = [
            DashboardExposureBand(
                key=key,
                label=label,
                count=by_class[key][0],
                targets=by_class[key][1],
                query=f"class:{key}",
            )
            for key, label in SERVICE_CLASS_LABELS.items()
            if key in by_class
        ]

        class_votes = (
            await self.session.execute(
                select(Port.service_name, Port.service_class, n)
                .where(scope, Port.service_name.isnot(None))
                .group_by(Port.service_name, Port.service_class)
            )
        ).all()
        klass: dict[str, tuple[int, str]] = {}
        for name, service_class, count in class_votes:
            if int(count) > klass.get(name, (0, ""))[0]:
                klass[name] = (int(count), str(service_class))

        per_scan = (
            await self.session.execute(
                select(Port.scan_id, Port.service_name, n, n.filter(sensitive))
                .where(scope, Port.service_name.isnot(None))
                .group_by(Port.scan_id, Port.service_name)
            )
        ).all()
        services: dict[str, DashboardExposedService] = {}
        for sid, name, count, sensitive_count in per_scan:
            if klass.get(name, (0, ""))[1] == ServiceClass.WEB.value:
                continue
            entry = services.setdefault(
                name,
                DashboardExposedService(
                    key=name,
                    label=service_label(name),
                    service_class=klass[name][1],
                    query=token("service", "=", name),
                ),
            )
            entry.count += int(count)
            entry.sensitive = entry.sensitive or int(sensitive_count) > 0
            scan = scans.get(sid)
            if scan is not None:
                entry.targets.append(
                    DashboardTargetCount(
                        target_id=scan.target_id,
                        target_value=names.get(scan.target_id, ""),
                        scan_id=sid,
                        count=int(count),
                    )
                )
        for entry in services.values():
            entry.targets.sort(key=lambda t: (-t.count, t.target_value))
        out.top = sorted(
            services.values(),
            key=lambda s: (not s.sensitive, -s.count, s.label),
        )[:EXPOSURE_TOP]
        return out

    async def _certs(
        self,
        certs: DashboardCerts,
        web_ids: list[UUID],
        now: datetime,
    ) -> None:
        if not web_ids:
            return
        expired = and_(cert_state("expired", now), live())
        not_after = Subdomain.tls_not_after
        filters = []
        for _key, _label, lower, upper in CERT_BUCKETS:
            if upper == 0:
                filters.append(expired)
                continue
            clauses = [live(), not_(cert_state("expired", now)), not_after.isnot(None)]
            if lower:
                clauses.append(not_after >= now + timedelta(days=lower))
            if upper is not None:
                clauses.append(not_after < now + timedelta(days=upper))
            filters.append(and_(*clauses))
        per_bucket = (
            await self.session.execute(
                select(*[func.count().filter(f) for f in filters]).where(
                    Subdomain.scan_id.in_(web_ids),
                    or_(not_after.isnot(None), Subdomain.tls_expired.is_(True)),
                )
            )
        ).one()
        buckets = [int(n or 0) for n in per_bucket]
        certs.buckets = [
            DashboardCertBucket(
                key=key,
                label=label,
                count=n,
                query=cert_bucket_query(lower, upper),
            )
            for (key, label, lower, upper), n in zip(CERT_BUCKETS, buckets, strict=True)
        ]

    async def _monitored(self, project_id: UUID) -> set[UUID]:
        result = await self.session.execute(
            select(ScanSchedule.target_ids).where(
                ScanSchedule.project_id == project_id,
                ScanSchedule.status == ScheduleStatus.ACTIVE.value,
            )
        )
        out: set[UUID] = set()
        for target_ids in result.scalars().all():
            for raw in target_ids or []:
                try:
                    out.add(UUID(str(raw)))
                except ValueError:
                    continue
        return out

    async def _changes(
        self,
        in_window: list[Scan],
        counts: Counts,
        firsts: dict[str, dict[UUID, int]],
        baselines: dict[str, set[UUID]],
        names: dict[UUID, str],
        targets: list[Target],
    ) -> list[DashboardChangeRow]:
        """Per target, what the window's runs were the first to report."""
        by_target: dict[UUID, list[Scan]] = defaultdict(list)
        for s in in_window:
            by_target[s.target_id].append(s)
        if not by_target:
            return []
        completed = [s.id for s in in_window if s.status == ScanStatus.COMPLETED.value]
        gone = await self.scans.gone_subdomain_counts(completed, list(by_target))
        types = {t.id: t.target_type.value for t in targets}
        out = []
        for tid, runs in by_target.items():
            runs.sort(key=_started, reverse=True)
            last = runs[0]
            row = DashboardChangeRow(
                target_id=tid,
                target_value=names.get(tid, ""),
                target_type=types.get(tid, ""),
                runs=len(runs),
                last_scan_id=last.id,
                last_status=last.status,
                last_at=_started(last),
            )
            for key in SURFACE_ORDER:
                total = sum(
                    firsts[key].get(s.id, 0) for s in runs if s.id in baselines[key]
                )
                if total:
                    row.new[key] = total
                elif any(
                    counts[key].get(s.id, (0, None))[0] and s.id not in baselines[key]
                    for s in runs
                ):
                    row.first.append(key)
            newest_done = next(
                (s.id for s in runs if s.status == ScanStatus.COMPLETED.value), None
            )
            row.gone_web_assets = gone.get(newest_done, 0) if newest_done else 0
            out.append(row)
        out.sort(
            key=lambda r: (
                -sum(r.new.values()),
                -r.gone_web_assets,
                -r.last_at.timestamp(),
            )
        )
        return out[:CHANGES_LIMIT]

    def _daily(
        self,
        scans: dict[UUID, Scan],
        firsts: dict[str, dict[UUID, int]],
        baselines: dict[str, set[UUID]],
        series_cutoff: datetime,
        now: datetime,
        covered: Covered,
        counts: Counts,
        retired: dict[str, dict[UUID, int]],
        severity_firsts: dict[UUID, dict[str, int]],
    ) -> list[DashboardDay]:
        days: dict[str, DashboardDay] = {}
        start = series_cutoff.date()
        for i in range((now.date() - start).days + 1):
            key = (start + timedelta(days=i)).isoformat()
            days[key] = DashboardDay(
                date=key,
                new=dict.fromkeys(SURFACE_ORDER, 0),
                retired=dict.fromkeys(SURFACE_ORDER, 0),
                total=dict.fromkeys(SURFACE_ORDER, 0),
                findings=dict.fromkeys(SEVERITY_ORDER, 0),
            )
        for key, per_target in covered.items():
            for ids in per_target.values():
                timeline = sorted(
                    (
                        (_started(scans[sid]), counts[key].get(sid, (0, None))[0])
                        for sid in ids
                    ),
                    key=lambda x: x[0],
                )
                if not timeline:
                    continue
                at = 0
                for day_key, day in days.items():
                    end = datetime.combine(
                        date.fromisoformat(day_key) + timedelta(days=1),
                        time.min,
                        tzinfo=UTC,
                    )
                    while at < len(timeline) and timeline[at][0] < end:
                        at += 1
                    if at:
                        day.total[key] += timeline[at - 1][1]
        for s in scans.values():
            key = _started(s).date().isoformat()
            day = days.get(key)
            if day is None:
                continue
            day.runs += 1
            if s.status in _TERMINAL_BAD:
                day.failed += 1
            day.outcomes[s.status] = day.outcomes.get(s.status, 0) + 1
            for dim in SURFACE_ORDER:
                if s.id in baselines[dim]:
                    day.new[dim] += firsts[dim].get(s.id, 0)
                day.retired[dim] += retired[dim].get(s.id, 0)
            if s.id in baselines[VULNS]:
                for severity, n in severity_firsts.get(s.id, {}).items():
                    day.findings[severity] = day.findings.get(severity, 0) + n
        return list(days.values())

    async def _retired(
        self, covered: Covered, scans: dict[UUID, Scan], series_cutoff: datetime
    ) -> dict[str, dict[UUID, int]]:
        """Per dimension, rows the previous covering run held that a completed run lacks."""
        out: dict[str, dict[UUID, int]] = {key: {} for key in _TABLES}
        for key in _TABLES:
            pairs: list[tuple[UUID, UUID]] = []
            for ids in covered[key].values():
                for newer, older in pairwise(ids):
                    scan = scans.get(newer)
                    if (
                        scan is None
                        or scan.status != ScanStatus.COMPLETED.value
                        or _started(scan) < series_cutoff
                    ):
                        continue
                    pairs.append((newer, older))
            if not pairs:
                continue
            counts = await stored_deltas.retired(self.session, key, pairs)
            out[key] = {newer: n for (newer, _), n in counts.items() if n}
        return out

    async def _addresses(self, ip_ids: list[UUID]) -> int:
        """Distinct addresses across the covering scans."""
        if not ip_ids:
            return 0
        return int(
            await self.session.scalar(
                select(func.count(func.distinct(IpAddress.ip))).where(
                    IpAddress.scan_id.in_(ip_ids)
                )
            )
            or 0
        )

    async def _answering(self, web_ids: list[UUID]) -> int:
        """Hosts that answered on HTTP at all, the `is:web` count."""
        if not web_ids:
            return 0
        return int(
            await self.session.scalar(
                select(func.count())
                .select_from(Subdomain)
                .where(Subdomain.scan_id.in_(web_ids), answered())
            )
            or 0
        )


def _stale_row(target: Target, last: datetime | None) -> StaleTarget:
    return StaleTarget(
        target_id=target.id,
        target_value=target.target_value,
        target_type=target.target_type.value,
        last_scanned_at=last,
    )
