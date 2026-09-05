from collections import defaultdict
from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, cast, func, not_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.asset_query.predicates import vuln_suppressed
from app.services.scan import ScanService
from shared.definitions.ports import SENSITIVE_PORTS
from shared.definitions.surface import (
    SURFACE_KINDS,
    SURFACE_LABELS,
    SURFACE_ORDER,
    SurfaceDimension,
)
from shared.definitions.vulnerabilities import (
    ACTIONABLE_SEVERITIES,
    SEVERITY_LABELS,
    SEVERITY_ORDER,
    Severity,
    coerce_severity,
)
from shared.enums.scan import SCAN_LIVE_STATUSES, ScanActivityStatus, ScanStatus
from shared.enums.scan_schedule import ScheduleStatus
from shared.models.endpoint import Endpoint
from shared.models.ip_address import IpAddress
from shared.models.port import Port
from shared.models.scan import Scan
from shared.models.scan_activity import ScanActivity
from shared.models.scan_schedule import ScanSchedule
from shared.models.subdomain import Subdomain
from shared.models.target_summary import (
    SurfaceMetric,
    TargetMonitoring,
    TargetRisk,
    TargetSummaryRead,
)
from shared.models.vulnerability import SeverityCount, Vulnerability
from shared.services.schedule_timing import describe_schedule
from stages.registry import stages

# the surface sweep looks this far back; totals still count every run
_MAX_RUNS = 25

_TABLES = {
    SurfaceDimension.WEB_ASSETS.value: Subdomain,
    SurfaceDimension.ENDPOINTS.value: Endpoint,
    SurfaceDimension.SERVICES.value: Port,
    SurfaceDimension.IPS.value: IpAddress,
    SurfaceDimension.VULNERABILITIES.value: Vulnerability,
}


def _covering_stages() -> dict[str, frozenset[str]]:
    """Dimension -> the stage names whose success means the dimension was scanned."""
    out: dict[str, set[str]] = {key: set() for key in SURFACE_ORDER}
    for spec in stages():
        for key, kinds in SURFACE_KINDS.items():
            if spec.produces & kinds:
                out[key].add(spec.name)
    return {key: frozenset(names) for key, names in out.items()}


class TargetSummaryService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.scans = ScanService(session)

    async def summary(self, target_id: UUID, project_id: UUID) -> TargetSummaryRead:
        runs = await self._runs(target_id, project_id)
        summary = TargetSummaryRead(target_id=target_id)
        if not runs:
            summary.monitoring = await self._monitoring(target_id, project_id)
            return summary

        summary.scans_total = len(runs)
        summary.scans_running = sum(1 for r in runs if r.status in SCAN_LIVE_STATUSES)
        summary.scans_failed = sum(
            1 for r in runs if r.status == ScanStatus.FAILED.value
        )
        summary.first_scan_at = _started(runs[-1])
        summary.last_scan_at = _started(runs[0])
        completed = [r for r in runs if r.status == ScanStatus.COMPLETED.value]
        summary.last_completed_at = completed[0].completed_at if completed else None

        latest = await self.scans.get(runs[0].id, project_id)
        summary.latest_scan = latest

        recent = runs[:_MAX_RUNS]
        counts = await self._counts(recent)
        covered = await self._covered(recent, counts)
        summary.surface = self._surface(recent, covered, counts, latest)

        vuln_scan = _pick(recent, covered[SurfaceDimension.VULNERABILITIES.value])
        if vuln_scan is not None:
            summary.risk = await self._risk(vuln_scan)
        service_scan = _pick(recent, covered[SurfaceDimension.SERVICES.value])
        if service_scan is not None:
            summary.sensitive_services = await self._sensitive(service_scan.id)

        total, first_seen = await self._inventory(target_id)
        summary.inventory_total = total
        summary.inventory_first_seen = first_seen
        summary.monitoring = await self._monitoring(target_id, project_id)
        return summary

    async def _runs(self, target_id: UUID, project_id: UUID) -> list[Scan]:
        result = await self.session.execute(
            select(Scan)
            .where(Scan.target_id == target_id, Scan.project_id == project_id)
            .order_by(func.coalesce(Scan.started_at, Scan.created_at).desc())
        )
        return list(result.scalars().all())

    async def _counts(self, runs: list[Scan]) -> dict[str, dict[UUID, int]]:
        """Rows this target's scans hold, per dimension. The count is the promise."""
        ids = [r.id for r in runs]
        out: dict[str, dict[UUID, int]] = {}
        for key, model in _TABLES.items():
            query: Select = (
                select(model.scan_id, func.count())
                .where(model.scan_id.in_(ids))
                .group_by(model.scan_id)
            )
            if key == SurfaceDimension.VULNERABILITIES.value:
                # every run here shares one target, so any of their ids resolves it
                query = query.where(not_(vuln_suppressed(ids[0])))
            result = await self.session.execute(query)
            out[key] = {row[0]: row[1] for row in result.all()}
        return out

    async def _covered(
        self, runs: list[Scan], counts: dict[str, dict[UUID, int]]
    ) -> dict[str, list[UUID]]:
        """Per dimension, the scans that ran it, newest first — rows count as proof."""
        ids = [r.id for r in runs]
        result = await self.session.execute(
            select(ScanActivity.scan_id, ScanActivity.name).where(
                ScanActivity.scan_id.in_(ids),
                ScanActivity.status == ScanActivityStatus.SUCCESS.value,
            )
        )
        ran: dict[UUID, set[str]] = defaultdict(set)
        for scan_id, name in result.all():
            ran[scan_id].add(name)

        by_dimension = _covering_stages()
        return {
            key: [
                r.id
                for r in runs
                if (ran[r.id] & names) or counts[key].get(r.id, 0) > 0
            ]
            for key, names in by_dimension.items()
        }

    def _surface(
        self,
        runs: list[Scan],
        covered: dict[str, list[UUID]],
        counts: dict[str, dict[UUID, int]],
        latest,
    ) -> list[SurfaceMetric]:
        by_id = {r.id: r for r in runs}
        metrics: list[SurfaceMetric] = []
        for key in SURFACE_ORDER:
            metric = SurfaceMetric(key=key, label=SURFACE_LABELS[key])
            scan_ids = covered[key][:2]
            if scan_ids:
                scan = by_id[scan_ids[0]]
                metric.covered = True
                metric.value = counts[key].get(scan.id, 0)
                metric.scan_id = scan.id
                metric.scan_status = scan.status
                metric.observed_at = _started(scan)
                metric.current = scan.id == runs[0].id
                if len(scan_ids) > 1:
                    metric.previous = counts[key].get(scan_ids[1], 0)
                    metric.delta = metric.value - metric.previous
            # a first covering scan has nothing to compare against, so it reports no change
            if (
                key == SurfaceDimension.WEB_ASSETS.value
                and latest is not None
                and metric.scan_id == latest.id
                and len(scan_ids) > 1
            ):
                metric.added = latest.new_subdomains
                metric.gone = latest.gone_subdomains
            metrics.append(metric)
        return metrics

    async def _risk(self, scan: Scan) -> TargetRisk:
        result = await self.session.execute(
            select(Vulnerability.severity, func.count())
            .where(
                Vulnerability.scan_id == scan.id,
                not_(vuln_suppressed(scan.id)),
            )
            .group_by(Vulnerability.severity)
        )
        tally: dict[str, int] = defaultdict(int)
        for severity, count in result.all():
            tally[coerce_severity(severity)] += count

        suppressed = await self.session.scalar(
            select(func.count())
            .select_from(Vulnerability)
            .where(Vulnerability.scan_id == scan.id, vuln_suppressed(scan.id))
        )
        kev = await self.session.scalar(
            select(func.count())
            .select_from(Vulnerability)
            .where(
                Vulnerability.scan_id == scan.id,
                Vulnerability.is_kev.is_(True),
                not_(vuln_suppressed(scan.id)),
            )
        )
        return TargetRisk(
            scan_id=scan.id,
            observed_at=_started(scan),
            total=sum(tally.values()),
            actionable=sum(tally[s] for s in ACTIONABLE_SEVERITIES),
            kev=int(kev or 0),
            suppressed=int(suppressed or 0),
            by_severity=[
                SeverityCount(
                    severity=s, label=SEVERITY_LABELS[s], count=tally.get(s, 0)
                )
                for s in SEVERITY_ORDER
                if tally.get(s, 0) > 0 or s != Severity.UNKNOWN.value
            ],
        )

    async def _sensitive(self, scan_id: UUID) -> int:
        value = await self.session.scalar(
            select(func.count())
            .select_from(Port)
            .where(Port.scan_id == scan_id, Port.number.in_(SENSITIVE_PORTS))
        )
        return int(value or 0)

    async def _inventory(self, target_id: UUID) -> tuple[int, datetime | None]:
        row = await self.session.execute(
            select(
                func.count(func.distinct(Subdomain.name)),
                func.min(Subdomain.discovered_at),
            ).where(Subdomain.target_id == target_id)
        )
        total, first_seen = row.one()
        return int(total or 0), first_seen

    async def _monitoring(
        self, target_id: UUID, project_id: UUID
    ) -> TargetMonitoring | None:
        result = await self.session.execute(
            select(ScanSchedule)
            .where(
                ScanSchedule.project_id == project_id,
                ScanSchedule.status == ScheduleStatus.ACTIVE.value,
                cast(ScanSchedule.target_ids, JSONB).contains([str(target_id)]),
            )
            .order_by(ScanSchedule.next_run_at.asc().nullslast())
            .limit(1)
        )
        schedule = result.scalar_one_or_none()
        if schedule is None:
            return None
        return TargetMonitoring(
            schedule_id=schedule.id,
            name=schedule.name,
            cadence=describe_schedule(schedule),
            status=schedule.status,
            next_run_at=schedule.next_run_at,
            last_run_at=schedule.last_run_at,
        )


def _started(scan: Scan) -> datetime:
    return scan.started_at or scan.created_at


def _pick(runs: list[Scan], scan_ids: list[UUID]) -> Scan | None:
    if not scan_ids:
        return None
    return next((r for r in runs if r.id == scan_ids[0]), None)
