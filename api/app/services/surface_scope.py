"""What a project-wide result view is looking at: the latest covering scan per target."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from sqlalchemy import distinct, exists, func, not_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.services.asset_query import QueryScope, vuln_suppressed
from shared.definitions.asset_query import COUNT_CAP
from shared.definitions.dashboard import STALE_DAYS
from shared.definitions.surface import (
    SURFACE_KINDS,
    SURFACE_LABELS,
    SURFACE_NOUN,
    SURFACE_ORDER,
    SurfaceDimension,
)
from shared.enums.scan import SCAN_LIVE_STATUSES, ScanActivityStatus
from shared.models.endpoint import Endpoint
from shared.models.ip_address import IpAddress
from shared.models.port import Port
from shared.models.scan import Scan
from shared.models.scan_activity import ScanActivity
from shared.models.subdomain import Subdomain
from shared.models.surface import SurfaceCoverage, SurfaceOverview, SurfaceTargetRead
from shared.models.target import Target
from shared.models.vulnerability import Vulnerability
from shared.services.scan_scope import census_only
from shared.utils.datetime import utc_now
from stages.registry import stages

TABLES = {
    SurfaceDimension.WEB_ASSETS.value: Subdomain,
    SurfaceDimension.ENDPOINTS.value: Endpoint,
    SurfaceDimension.SERVICES.value: Port,
    SurfaceDimension.IPS.value: IpAddress,
    SurfaceDimension.VULNERABILITIES.value: Vulnerability,
}


def covering_stages() -> dict[str, frozenset[str]]:
    """Dimension -> the stage names whose success means the dimension was scanned."""
    out: dict[str, set[str]] = {key: set() for key in SURFACE_ORDER}
    for spec in stages():
        for key, kinds in SURFACE_KINDS.items():
            if spec.produces & kinds:
                out[key].add(spec.name)
    return {key: frozenset(names) for key, names in out.items()}


async def baselined_targets(
    session: AsyncSession, model, scope: QueryScope
) -> set[UUID]:
    """The scope's targets an earlier scan already recorded this dimension for.

    A project view spans targets on their first scan and targets with years of history,
    so "new" has to be asked per target or a first scan marks everything new.
    """
    if not scope.ids:
        return set()
    earlier = aliased(model)
    cutoff = (
        select(func.min(model.discovered_at))
        .where(model.scan_id == Scan.id)
        .correlate(Scan)
        .scalar_subquery()
    )
    rows = await session.execute(
        select(Scan.target_id).where(
            Scan.id.in_(scope.ids),
            exists(
                select(1).where(
                    earlier.target_id == Scan.target_id,
                    earlier.scan_id != Scan.id,
                    earlier.discovered_at < cutoff,
                )
            ),
        )
    )
    return {row[0] for row in rows.all()}


def _started():
    return func.coalesce(Scan.started_at, Scan.created_at)


class SurfaceScopeService:
    def __init__(self, session: AsyncSession):
        self.session = session
        # one instance per request, so these answer the same question every time
        self._picked: dict[tuple[UUID, str], list] = {}
        self._targets_by_project: dict[UUID, dict[UUID, Target]] = {}

    async def scope(self, project_id: UUID, dimension: str) -> QueryScope:
        picks = await self._picks(project_id, dimension)
        return QueryScope(tuple(row.id for row in picks), project_id=project_id)

    async def _picks(self, project_id: UUID, dimension: str):
        """The newest scan of each target that actually ran this dimension."""
        cached = self._picked.get((project_id, dimension))
        if cached is not None:
            return cached
        model = TABLES[dimension]
        names = covering_stages()[dimension]
        rows = await self.session.execute(
            select(Scan.id, Scan.target_id, Scan.status, _started().label("at"))
            .where(
                Scan.project_id == project_id,
                census_only(),
                exists(select(1).where(model.scan_id == Scan.id))
                | exists(
                    select(1).where(
                        ScanActivity.scan_id == Scan.id,
                        ScanActivity.status == ScanActivityStatus.SUCCESS.value,
                        ScanActivity.name.in_(names),
                    )
                ),
            )
            .distinct(Scan.target_id)
            .order_by(Scan.target_id, _started().desc())
        )
        picks = list(rows.all())
        self._picked[(project_id, dimension)] = picks
        return picks

    async def _targets(self, project_id: UUID) -> dict[UUID, Target]:
        cached = self._targets_by_project.get(project_id)
        if cached is not None:
            return cached
        rows = await self.session.execute(
            select(Target).where(Target.project_id == project_id)
        )
        targets = {row.id: row for row in rows.scalars().all()}
        self._targets_by_project[project_id] = targets
        return targets

    async def _count(self, dimension: str, scope: QueryScope) -> tuple[int, bool]:
        if not scope:
            return 0, False
        if dimension == SurfaceDimension.IPS.value:
            # one row per address, so the count has to come from the table's own query
            from app.services.ip_address import IpAddressService  # noqa: PLC0415

            derived = IpAddressService._derived(scope)
            inner = select(derived.c.ip).select_from(derived)
        else:
            model = TABLES[dimension]
            inner = select(model.id).where(scope.match(model.scan_id))
            if dimension == SurfaceDimension.VULNERABILITIES.value:
                inner = inner.where(not_(vuln_suppressed(scope)))
        counted = await self.session.scalar(
            select(func.count()).select_from(inner.limit(COUNT_CAP + 1).subquery())
        )
        total = int(counted or 0)
        return min(total, COUNT_CAP), total > COUNT_CAP

    async def coverage(
        self, project_id: UUID, dimension: str, *, counts: bool = True
    ) -> SurfaceCoverage:
        picks = await self._picks(project_id, dimension)
        targets = await self._targets(project_id)
        scope = QueryScope(tuple(row.id for row in picks), project_id=project_id)
        noun, noun_plural = SURFACE_NOUN[dimension]
        out = SurfaceCoverage(
            dimension=dimension,
            label=SURFACE_LABELS[dimension],
            noun=noun,
            noun_plural=noun_plural,
            targets_total=len(targets),
        )
        cutoff = utc_now() - timedelta(days=STALE_DAYS)
        seen: set[UUID] = set()
        for row in picks:
            target = targets.get(row.target_id)
            if target is None:
                continue
            seen.add(row.target_id)
            out.covered.append(
                SurfaceTargetRead(
                    target_id=target.id,
                    target_value=target.target_value,
                    target_type=target.target_type,
                    scan_id=row.id,
                    scan_status=row.status,
                    observed_at=row.at,
                    stale=bool(row.at and row.at < cutoff),
                )
            )
        out.covered.sort(key=lambda r: r.target_value)
        out.uncovered = sorted(
            (
                SurfaceTargetRead(
                    target_id=target.id,
                    target_value=target.target_value,
                    target_type=target.target_type,
                )
                for target_id, target in targets.items()
                if target_id not in seen
            ),
            key=lambda r: r.target_value,
        )
        out.targets_covered = len(out.covered)
        stamps = [r.observed_at for r in out.covered if r.observed_at]
        out.observed_from = min(stamps) if stamps else None
        out.observed_to = max(stamps) if stamps else None
        if counts:
            out.total, out.total_capped = await self._count(dimension, scope)
        return out

    async def overview(self, project_id: UUID) -> SurfaceOverview:
        targets_total = await self.session.scalar(
            select(func.count()).select_from(
                select(Target.id).where(Target.project_id == project_id).subquery()
            )
        )
        live = await self.session.scalar(
            select(func.count(distinct(Scan.id))).where(
                Scan.project_id == project_id,
                Scan.status.in_(SCAN_LIVE_STATUSES),
            )
        )
        out = SurfaceOverview(
            project_id=project_id,
            targets_total=int(targets_total or 0),
            live_scans=int(live or 0),
            generated_at=utc_now(),
        )
        for dimension in SURFACE_ORDER:
            out.dimensions.append(await self.coverage(project_id, dimension))
        out.exposures = await self._exposures(project_id)
        return out

    async def _exposures(self, project_id: UUID) -> int:
        """Assets flagged for what they are; a judgement over web assets, not a dimension."""
        scope = await self.scope(project_id, SurfaceDimension.WEB_ASSETS.value)
        if not scope:
            return 0
        counted = await self.session.scalar(
            select(func.count()).where(
                scope.match(Subdomain.scan_id),
                Subdomain.interest_band.isnot(None),
            )
        )
        return int(counted or 0)
