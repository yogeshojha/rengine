from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import Text, and_, case, cast, exists, func, not_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.asset_query.predicates import cert_state, live, vuln_seen_earlier
from app.services.dashboard import DashboardService
from app.services.related_domains import RelatedDomainService
from app.services.scan import ScanService
from app.services.target_summary import _covering_stages
from shared.definitions.dashboard import (
    CHANGES_LIMIT,
    DEFAULT_WINDOW,
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
    WINDOW_DELTAS,
)
from shared.definitions.domains import MAX_RELATED_HOSTNAMES
from shared.definitions.ports import (
    SENSITIVE_PORTS,
    SERVICE_CLASS_LABELS,
    ServiceClass,
    service_label,
)
from shared.definitions.surface import SURFACE_LABELS, SURFACE_ORDER, SurfaceDimension
from shared.definitions.vulnerabilities import (
    ACTIONABLE_SEVERITIES,
    SEVERITY_LABELS,
    SEVERITY_ORDER,
    SUPPRESSED_STATES,
    Severity,
    coerce_severity,
)
from shared.enums.scan import ScanActivityStatus, ScanStatus
from shared.enums.scan_schedule import ScheduleStatus
from shared.enums.target import TargetType
from shared.models.dashboard import (
    DashboardCerts,
    DashboardCertSignal,
    DashboardChangeRow,
    DashboardDay,
    DashboardDiscoveredDomain,
    DashboardDiscovery,
    DashboardDiscoverySource,
    DashboardExposedService,
    DashboardExposure,
    DashboardExposureBand,
    DashboardFinding,
    DashboardGeo,
    DashboardOverview,
    DashboardRisk,
    DashboardSurfaceMetric,
    DashboardTargetCount,
    DashboardTargetRow,
    DashboardTargetSurface,
    ExpiringTarget,
    FailedRun,
    StaleTarget,
)
from shared.models.endpoint import Endpoint
from shared.models.http_asset import HttpAsset
from shared.models.ip_address import IpAddress
from shared.models.port import Port
from shared.models.scan import Scan
from shared.models.scan_activity import ScanActivity
from shared.models.scan_schedule import ScanSchedule
from shared.models.subdomain import Subdomain
from shared.models.target import Target
from shared.models.vulnerability import (
    SeverityCount,
    Vulnerability,
    VulnerabilityTriage,
)
from shared.models.whois import WhoisRecord
from shared.services.scan_scope import census_only
from shared.utils.datetime import utc_now

WEB = SurfaceDimension.WEB_ASSETS.value
ENDPOINTS = SurfaceDimension.ENDPOINTS.value
SERVICES = SurfaceDimension.SERVICES.value
IPS = SurfaceDimension.IPS.value
VULNS = SurfaceDimension.VULNERABILITIES.value

_TABLES = {
    WEB: Subdomain,
    ENDPOINTS: Endpoint,
    SERVICES: Port,
    IPS: IpAddress,
    VULNS: Vulnerability,
}
_KEYS = {
    WEB: (Subdomain.name,),
    ENDPOINTS: (Endpoint.signature,),
    SERVICES: (Port.ip, Port.number, Port.protocol),
    IPS: (IpAddress.ip,),
    VULNS: (Vulnerability.fingerprint,),
}
_TERMINAL_BAD = (ScanStatus.FAILED.value, ScanStatus.CANCELLED.value)
_DOMAIN_TYPES = (TargetType.DOMAIN, TargetType.URL)
_BARE_TOKEN = re.compile(r"^[\w.\-]+$")

Counts = dict[str, dict[UUID, tuple[int, datetime]]]
Covered = dict[str, dict[UUID, list[UUID]]]


def _started(scan: Scan) -> datetime:
    return scan.started_at or scan.created_at


def _exact(key: str, value: str) -> str:
    if _BARE_TOKEN.match(value):
        return f"{key}={value}"
    quoted = value.replace('"', '\\"')
    return f'{key}="{quoted}"'


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


class DashboardOverviewService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.signals = DashboardService(session)
        self.scans = ScanService(session)

    async def overview(self, project_id: UUID, window: str) -> DashboardOverview:
        if window not in WINDOW_DELTAS:
            window = DEFAULT_WINDOW
        now = utc_now()
        cutoff = now - WINDOW_DELTAS[window]
        series_cutoff = now - timedelta(days=SERIES_DAYS)

        targets, expires = await self._targets(project_id)
        runs_by_target, runs_total = await self._runs(project_id, series_cutoff)
        scans: dict[UUID, Scan] = {
            s.id: s for runs in runs_by_target.values() for s in runs
        }
        counts = await self._counts(project_id)
        ran = await self._ran(list(scans))
        covered = self._covered(runs_by_target, counts, ran)
        firsts = await self._first_seen(project_id)
        baselines = self._baselines(counts, scans)
        names = {t.id: t.target_value for t in targets}

        signals = await self.signals.signals(project_id)
        out = DashboardOverview(
            generated_at=now,
            window=window,
            signals=signals,
            runs_total=runs_total,
            certs=DashboardCerts(
                expired=DashboardCertSignal(query=EXPIRED_CERT_QUERY),
                expiring=DashboardCertSignal(query=EXPIRING_CERT_QUERY),
            ),
        )
        out.first_run = await self._first_run()
        out.targets_total = len(targets)
        out.targets_scanned = sum(1 for t in targets if runs_by_target.get(t.id))
        by_type: dict[str, int] = defaultdict(int)
        for t in targets:
            by_type[t.target_type.value] += 1
        out.targets_by_type = dict(by_type)

        in_window = [s for s in scans.values() if _started(s) >= cutoff]
        out.runs_in_window = len(in_window)
        out.failed_in_window = sum(1 for s in in_window if s.status in _TERMINAL_BAD)
        out.last_completed_at = max(
            (s.completed_at for s in scans.values() if s.completed_at), default=None
        )

        latest_cover = {
            key: {tid: ids[0] for tid, ids in per_target.items() if ids}
            for key, per_target in covered.items()
        }
        out.surface = self._surface(counts, latest_cover, firsts, baselines, in_window)

        risk_ids = list(latest_cover[VULNS].values())
        out.risk = await self._risk(risk_ids, firsts, baselines, in_window)
        risk_by_target = await self._risk_by_target(risk_ids)

        service_ids = list(latest_cover[SERVICES].values())
        sensitive = await self._sensitive(service_ids)
        out.exposure = await self._exposure(service_ids, scans, names)
        await self._certs(
            out.certs, list(latest_cover[WEB].values()), scans, names, now
        )
        ip_ids = list(latest_cover[IPS].values())
        out.geography, out.geo_total = await self._geography(ip_ids, names, scans)

        monitored = await self._monitored(project_id)
        out.targets_monitored = sum(1 for t in targets if t.id in monitored)

        self._items(out, targets, runs_by_target, scans, sensitive, expires, now)
        out.changes = await self._changes(
            in_window, counts, firsts, baselines, names, targets
        )
        out.daily = self._daily(scans, firsts, baselines, series_cutoff, now)
        out.targets = self._target_rows(
            targets,
            runs_by_target,
            counts,
            covered,
            risk_by_target,
            sensitive,
            latest_cover,
            monitored,
        )
        return out

    async def discovery(self, project_id: UUID) -> DashboardDiscovery:
        """Registrable domains the estate's certificates vouch for that are not targets."""
        newest = (
            select(
                HttpAsset.target_id,
                HttpAsset.scan_id,
                func.max(HttpAsset.discovered_at).label("at"),
            )
            .join(Target, Target.id == HttpAsset.target_id)
            .where(
                HttpAsset.project_id == project_id,
                Target.target_type.in_(_DOMAIN_TYPES),
            )
            .group_by(HttpAsset.target_id, HttpAsset.scan_id)
        )
        latest: dict[UUID, tuple[datetime, UUID]] = {}
        for tid, sid, at in (await self.session.execute(newest)).all():
            if tid not in latest or at > latest[tid][0]:
                latest[tid] = (at, sid)
        out = DashboardDiscovery(targets_examined=len(latest))
        if not latest:
            return out
        names = dict(
            (
                await self.session.execute(
                    select(Target.id, Target.target_value).where(
                        Target.id.in_(list(latest))
                    )
                )
            ).all()
        )
        related = RelatedDomainService(self.session)
        merged: dict[str, DashboardDiscoveredDomain] = {}
        for tid, (_at, sid) in latest.items():
            result = await related.for_scan(project_id, sid)
            for d in result.domains:
                if d.is_target:
                    continue
                entry = merged.setdefault(
                    d.domain, DashboardDiscoveredDomain(domain=d.domain)
                )
                entry.hostnames = sorted(set(entry.hostnames) | set(d.hostnames))[
                    :MAX_RELATED_HOSTNAMES
                ]
                entry.hostname_count = max(entry.hostname_count, d.hostname_count)
                entry.sources.append(
                    DashboardDiscoverySource(
                        target_id=tid,
                        target_value=names.get(tid, ""),
                        scan_id=sid,
                        seen_on=d.evidence[0].seen_on if d.evidence else "",
                        hostname_count=d.hostname_count,
                    )
                )
        for entry in merged.values():
            entry.sources.sort(key=lambda s: (-s.hostname_count, s.target_value))
        out.domains = sorted(
            merged.values(),
            key=lambda d: (-len(d.sources), -d.hostname_count, d.domain),
        )[:DISCOVERY_LIMIT]
        return out

    def _items(
        self,
        out: DashboardOverview,
        targets: list[Target],
        runs_by_target: dict[UUID, list[Scan]],
        scans: dict[UUID, Scan],
        sensitive: dict[UUID, int],
        expires: dict[UUID, datetime | None],
        now: datetime,
    ) -> None:
        """The item lists behind the attention tiles."""
        names = {t.id: t.target_value for t in targets}
        stale_before = now - timedelta(days=STALE_DAYS)
        for t in targets:
            runs = runs_by_target.get(t.id)
            if not runs:
                out.never_scanned.append(_stale_row(t, None))
            elif _started(runs[0]) < stale_before:
                out.stale.append(_stale_row(t, _started(runs[0])))
        out.never_scanned.sort(key=lambda x: x.target_value)
        out.stale.sort(key=lambda x: x.last_scanned_at or now)
        out.targets_never_scanned = len(out.never_scanned)
        out.targets_stale = len(out.stale)
        out.never_scanned = out.never_scanned[:ITEMS_CAP]
        out.stale = out.stale[:ITEMS_CAP]
        out.sensitive = sorted(
            (
                DashboardTargetCount(
                    target_id=scans[sid].target_id,
                    target_value=names.get(scans[sid].target_id, ""),
                    scan_id=sid,
                    count=n,
                )
                for sid, n in sensitive.items()
                if n > 0
            ),
            key=lambda x: (-x.count, x.target_value),
        )[:ITEMS_CAP]
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
        out.failed_runs = [
            FailedRun(
                target_id=t.id,
                target_value=t.target_value,
                scan_id=runs[0].id,
                engine_name=runs[0].engine_name,
                error=runs[0].error,
                at=runs[0].completed_at or _started(runs[0]),
            )
            for t in targets
            if (runs := runs_by_target.get(t.id))
            and runs[0].status == ScanStatus.FAILED.value
        ][:ITEMS_CAP]

    async def _targets(
        self, project_id: UUID
    ) -> tuple[list[Target], dict[UUID, datetime | None]]:
        result = await self.session.execute(
            select(Target, WhoisRecord.expiration_date)
            .join(WhoisRecord, WhoisRecord.id == Target.whois_record_id, isouter=True)
            .where(Target.project_id == project_id)
            .order_by(Target.target_value.asc())
        )
        targets = []
        expires: dict[UUID, datetime | None] = {}
        for target, expires_at in result.all():
            targets.append(target)
            expires[target.id] = expires_at
        return targets, expires

    async def _first_run(self) -> bool:
        return not await self.session.scalar(
            select(
                exists().where(Scan.status == ScanStatus.COMPLETED.value, census_only())
            )
        )

    async def _runs(
        self, project_id: UUID, series_cutoff: datetime
    ) -> tuple[dict[UUID, list[Scan]], int]:
        """The latest runs per target plus everything inside the series window."""
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
            .where(Scan.project_id == project_id, census_only())
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
            select(func.count())
            .select_from(Scan)
            .where(Scan.project_id == project_id, census_only())
        )
        return by_target, int(total or 0)

    async def _counts(self, project_id: UUID) -> Counts:
        """Rows per scan and when its first row landed, per dimension."""
        out: Counts = {}
        for key, model in _TABLES.items():
            query = (
                select(model.scan_id, func.count(), func.min(model.discovered_at))
                .where(model.project_id == project_id)
                .group_by(model.scan_id)
            )
            if key == VULNS:
                query = query.where(not_(_suppressed()))
            result = await self.session.execute(query)
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

    def _covered(
        self,
        runs_by_target: dict[UUID, list[Scan]],
        counts: Counts,
        ran: dict[UUID, set[str]],
    ) -> Covered:
        """Per dimension and target, the scans that ran it, newest first."""
        by_dimension = _covering_stages()
        out: Covered = {key: {} for key in SURFACE_ORDER}
        for tid, runs in runs_by_target.items():
            for key, names in by_dimension.items():
                out[key][tid] = [
                    r.id
                    for r in runs
                    if (ran.get(r.id, set()) & names) or r.id in counts[key]
                ]
        return out

    async def _first_seen(self, project_id: UUID) -> dict[str, dict[UUID, int]]:
        """Per dimension, how many keys each scan was the first to report for its target."""
        out: dict[str, dict[UUID, int]] = {}
        for key, model in _TABLES.items():
            rn = (
                func.row_number()
                .over(
                    partition_by=[model.target_id, *_KEYS[key]],
                    order_by=[model.discovered_at.asc(), model.scan_id.asc()],
                )
                .label("rn")
            )
            firsts = select(model.scan_id.label("scan_id"), rn).where(
                model.project_id == project_id
            )
            if key == VULNS:
                firsts = firsts.where(not_(_suppressed()))
            firsts = firsts.subquery()
            result = await self.session.execute(
                select(firsts.c.scan_id, func.count())
                .where(firsts.c.rn == 1)
                .group_by(firsts.c.scan_id)
            )
            out[key] = {row[0]: int(row[1]) for row in result.all()}
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
        firsts: dict[str, dict[UUID, int]],
        baselines: dict[str, set[UUID]],
        in_window: list[Scan],
    ) -> list[DashboardSurfaceMetric]:
        out = []
        for key in SURFACE_ORDER:
            cover = latest_cover[key]
            metric = DashboardSurfaceMetric(key=key, label=SURFACE_LABELS[key])
            metric.targets_covered = len(cover)
            metric.value = sum(
                counts[key].get(sid, (0, None))[0] for sid in cover.values()
            )
            metric.new_in_window = sum(
                firsts[key].get(s.id, 0) for s in in_window if s.id in baselines[key]
            )
            out.append(metric)
        return out

    async def _risk(
        self,
        risk_ids: list[UUID],
        firsts: dict[str, dict[UUID, int]],
        baselines: dict[str, set[UUID]],
        in_window: list[Scan],
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
            )
            .where(live_rows, not_(_suppressed()))
            .group_by(Vulnerability.target_id, Vulnerability.template_id)
            .subquery()
        )
        rows = await self.session.execute(
            select(Vulnerability, spread.c.hosts, Target.target_value)
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
        for row, hosts, target_value in items:
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
                )
            )
        return out

    async def _risk_by_target(
        self, risk_ids: list[UUID]
    ) -> dict[UUID, tuple[int, int, int, str | None]]:
        """Per target: findings, actionable, KEV and the worst severity, from its risk scan."""
        if not risk_ids:
            return {}
        rank = _severity_rank()
        rows = await self.session.execute(
            select(
                Vulnerability.target_id,
                func.count(),
                func.count().filter(Vulnerability.severity.in_(ACTIONABLE_SEVERITIES)),
                func.count().filter(Vulnerability.is_kev.is_(True)),
                func.min(rank),
            )
            .where(Vulnerability.scan_id.in_(risk_ids), not_(_suppressed()))
            .group_by(Vulnerability.target_id)
        )
        out = {}
        for tid, total, actionable, kev, worst in rows.all():
            index = int(worst) if worst is not None else len(SEVERITY_ORDER)
            worst_name = SEVERITY_ORDER[index] if index < len(SEVERITY_ORDER) else None
            out[tid] = (int(total), int(actionable), int(kev), worst_name)
        return out

    async def _sensitive(self, service_ids: list[UUID]) -> dict[UUID, int]:
        if not service_ids:
            return {}
        rows = await self.session.execute(
            select(Port.scan_id, func.count())
            .where(Port.scan_id.in_(service_ids), Port.number.in_(SENSITIVE_PORTS))
            .group_by(Port.scan_id)
        )
        return {row[0]: int(row[1]) for row in rows.all()}

    async def _exposure(
        self, service_ids: list[UUID], scans: dict[UUID, Scan], names: dict[UUID, str]
    ) -> DashboardExposure:
        """What is listening across every target's latest service scan."""
        out = DashboardExposure(targets=len(service_ids))
        if not service_ids:
            return out
        scope = Port.scan_id.in_(service_ids)
        sensitive = Port.number.in_(SENSITIVE_PORTS)
        web = Port.service_class == ServiceClass.WEB.value
        n = func.count()
        totals = (
            await self.session.execute(
                select(
                    n,
                    func.count(func.distinct(Port.ip)),
                    n.filter(sensitive),
                    func.count(func.distinct(Port.scan_id)).filter(sensitive),
                    n.filter(not_(web)),
                ).where(scope)
            )
        ).one()
        (
            out.services,
            out.addresses,
            out.sensitive,
            out.sensitive_targets,
            out.non_web,
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
                    query=_exact("service", name),
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
        scans: dict[UUID, Scan],
        names: dict[UUID, str],
        now: datetime,
    ) -> None:
        if not web_ids:
            return
        expired = and_(cert_state("expired", now), live())
        expiring = cert_state("expiring", now)
        rows = (
            await self.session.execute(
                select(
                    Subdomain.scan_id,
                    func.count().filter(expired),
                    func.count().filter(expiring),
                )
                .where(Subdomain.scan_id.in_(web_ids))
                .group_by(Subdomain.scan_id)
            )
        ).all()
        for sid, n_expired, n_expiring in rows:
            scan = scans.get(sid)
            if scan is None:
                continue
            for signal, count in (
                (certs.expired, int(n_expired or 0)),
                (certs.expiring, int(n_expiring or 0)),
            ):
                if count:
                    signal.count += count
                    signal.targets.append(
                        DashboardTargetCount(
                            target_id=scan.target_id,
                            target_value=names.get(scan.target_id, ""),
                            scan_id=sid,
                            count=count,
                        )
                    )
        for signal in (certs.expired, certs.expiring):
            signal.targets.sort(key=lambda t: (-t.count, t.target_value))

    async def _geography(
        self, ip_ids: list[UUID], names: dict[UUID, str], scans: dict[UUID, Scan]
    ) -> tuple[list[DashboardGeo], int]:
        if not ip_ids:
            return [], 0
        located = (
            IpAddress.scan_id.in_(ip_ids),
            IpAddress.country.is_not(None),
            IpAddress.country != "",
        )
        totals = await self.session.execute(
            select(IpAddress.country, func.count(func.distinct(IpAddress.ip)))
            .where(*located)
            .group_by(IpAddress.country)
        )
        per_target = await self.session.execute(
            select(
                IpAddress.country,
                IpAddress.scan_id,
                func.count(func.distinct(IpAddress.ip)),
            )
            .where(*located)
            .group_by(IpAddress.country, IpAddress.scan_id)
        )
        breakdown: dict[str, list[DashboardTargetCount]] = defaultdict(list)
        for country, scan_id, count in per_target.all():
            scan = scans.get(scan_id)
            if scan is None:
                continue
            breakdown[country.upper()].append(
                DashboardTargetCount(
                    target_id=scan.target_id,
                    target_value=names.get(scan.target_id, ""),
                    scan_id=scan_id,
                    count=int(count),
                )
            )
        out = []
        for country, count in totals.all():
            code = country.upper()
            rows = sorted(
                breakdown.get(code, []), key=lambda r: (-r.count, r.target_value)
            )
            out.append(DashboardGeo(code=code, count=int(count), targets=rows))
        out.sort(key=lambda g: (-g.count, g.code))
        total = int(
            await self.session.scalar(
                select(func.count(func.distinct(IpAddress.ip))).where(*located)
            )
            or 0
        )
        return out, total

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
                contributors = [
                    s.id
                    for s in runs
                    if s.id in baselines[key] and firsts[key].get(s.id, 0)
                ]
                total = sum(firsts[key].get(sid, 0) for sid in contributors)
                if total:
                    row.new[key] = total
                    row.new_scan[key] = (
                        contributors[0] if len(contributors) == 1 else None
                    )
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
    ) -> list[DashboardDay]:
        days: dict[str, DashboardDay] = {}
        start = series_cutoff.date() + timedelta(days=1)
        for i in range((now.date() - start).days + 1):
            key = (start + timedelta(days=i)).isoformat()
            days[key] = DashboardDay(date=key, new=dict.fromkeys(SURFACE_ORDER, 0))
        for s in scans.values():
            key = _started(s).date().isoformat()
            day = days.get(key)
            if day is None:
                continue
            day.runs += 1
            if s.status in _TERMINAL_BAD:
                day.failed += 1
            for dim in SURFACE_ORDER:
                if s.id in baselines[dim]:
                    day.new[dim] += firsts[dim].get(s.id, 0)
        return list(days.values())

    def _target_rows(
        self,
        targets: list[Target],
        runs_by_target: dict[UUID, list[Scan]],
        counts: Counts,
        covered: Covered,
        risk_by_target: dict[UUID, tuple[int, int, int, str | None]],
        sensitive: dict[UUID, int],
        latest_cover: dict[str, dict[UUID, UUID]],
        monitored: set[UUID],
    ) -> list[DashboardTargetRow]:
        out = []
        for t in targets:
            runs = runs_by_target.get(t.id, [])
            row = DashboardTargetRow(
                id=t.id,
                value=t.target_value,
                type=t.target_type.value,
                scans_total=len(runs),
                monitored=t.id in monitored,
            )
            by_id = {r.id: r for r in runs}
            if runs:
                row.last_scan_id = runs[0].id
                row.last_scan_status = runs[0].status
                row.last_scan_at = _started(runs[0])
            for key in SURFACE_ORDER:
                metric = DashboardTargetSurface(key=key)
                ids = covered[key].get(t.id, [])[:2]
                if ids:
                    scan = by_id[ids[0]]
                    metric.covered = True
                    metric.value = counts[key].get(scan.id, (0, None))[0]
                    metric.scan_id = scan.id
                    metric.scan_status = scan.status
                    metric.observed_at = _started(scan)
                    if len(ids) > 1:
                        metric.previous = counts[key].get(ids[1], (0, None))[0]
                        metric.delta = metric.value - metric.previous
                row.surface.append(metric)
            risk = risk_by_target.get(t.id)
            if risk:
                row.findings, row.actionable, row.kev, row.worst_severity = risk
            row.risk_scan_id = latest_cover[VULNS].get(t.id)
            services_scan = latest_cover[SERVICES].get(t.id)
            row.services_scan_id = services_scan
            if services_scan:
                row.sensitive_services = sensitive.get(services_scan, 0)
            out.append(row)
        return out


def _stale_row(target: Target, last: datetime | None) -> StaleTarget:
    return StaleTarget(
        target_id=target.id,
        target_value=target.target_value,
        target_type=target.target_type.value,
        last_scanned_at=last,
    )
