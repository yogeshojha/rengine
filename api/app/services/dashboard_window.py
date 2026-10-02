"""What the dashboard window first reported, counted the way each dimension's page counts it."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.surface_scope import TABLES, SurfaceScopeService
from app.services.target_scope import Targets
from shared.definitions.asset_query import COUNT_CAP
from shared.definitions.dashboard import new_in_window, window_key, window_since
from shared.definitions.surface import SURFACE_ORDER, SurfaceDimension
from shared.definitions.vulnerabilities import coerce_severity
from shared.models.dashboard import DashboardWindowCount, DashboardWindowCounts
from shared.models.subdomain import Subdomain
from shared.models.vulnerability import Vulnerability
from shared.services.asset_query import QueryScope, lead_cache
from shared.services.asset_query.errors import NO_JIT, STATEMENT_TIMEOUT
from shared.services.surface_query import Built, for_dimension
from shared.utils.datetime import utc_now

WEB = SurfaceDimension.WEB_ASSETS.value
VULNS = SurfaceDimension.VULNERABILITIES.value

_SOURCE_KEYS = {
    SurfaceDimension.SERVICES.value: lambda d: [d.c.id],
    SurfaceDimension.IPS.value: lambda d: [d.c.ip],
}


class DashboardWindowService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.surfaces = SurfaceScopeService(session)

    async def counts(
        self, project_id: UUID, window: str, targets: Targets = None
    ) -> DashboardWindowCounts:
        window = window_key(window)
        scopes = {
            key: await self.surfaces.scope(project_id, key, targets=targets)
            for key in SURFACE_ORDER
        }
        scans = tuple(sorted({sid for scope in scopes.values() for sid in scope.ids}))
        picked = "" if targets is None else ",".join(sorted(map(str, targets)))
        return await lead_cache.cached(
            self.session,
            name="dashboard_window",
            scans=scans,
            facets=f"{project_id}|{window}|{picked}",
            model=DashboardWindowCounts,
            build=lambda: self._build(project_id, window, scopes),
            ttl=lead_cache.SEARCH_TTL_SECONDS,
        )

    async def _build(
        self, project_id: UUID, window: str, scopes: dict[str, QueryScope]
    ) -> DashboardWindowCounts:
        now = utc_now()
        query = new_in_window(window)
        out = DashboardWindowCounts(window=window, since=window_since(window, now))
        await self.session.execute(text(STATEMENT_TIMEOUT))
        await self.session.execute(text(NO_JIT))
        for key in SURFACE_ORDER:
            count, capped = await self._count(project_id, key, scopes[key], query, now)
            out.new.append(
                DashboardWindowCount(key=key, query=query, count=count, capped=capped)
            )
        out.findings = await self._findings(project_id, scopes[VULNS], query, now)
        out.targets_with_new_web_assets = await self._targets(
            project_id, scopes[WEB], query, now
        )
        return out

    def _filtered(
        self,
        project_id: UUID,
        key: str,
        scope: QueryScope,
        query: str,
        now: datetime,
        columns=None,
    ) -> Built:
        surface = for_dimension(key)
        f = surface.filter_model.model_validate({"q": query})
        if columns is None:
            columns = _SOURCE_KEYS.get(key) or [TABLES[key].id]
        return surface.filtered(scope, f, now, project_id=project_id, columns=columns)

    async def _count(
        self, project_id: UUID, key: str, scope: QueryScope, query: str, now: datetime
    ) -> tuple[int, bool]:
        if not scope:
            return 0, False
        built = self._filtered(project_id, key, scope, query, now)
        counted = await self.session.scalar(
            select(func.count()).select_from(
                built.statement.limit(COUNT_CAP + 1).subquery()
            )
        )
        total = int(counted or 0)
        return min(total, COUNT_CAP), total > COUNT_CAP

    async def _findings(
        self, project_id: UUID, scope: QueryScope, query: str, now: datetime
    ) -> dict[str, int]:
        if not scope:
            return {}
        rows = self._filtered(
            project_id, VULNS, scope, query, now, columns=[Vulnerability.severity]
        ).statement.subquery()
        out: dict[str, int] = {}
        for severity, n in await self.session.execute(
            select(rows.c.severity, func.count()).group_by(rows.c.severity)
        ):
            key = coerce_severity(severity)
            out[key] = out.get(key, 0) + int(n)
        return out

    async def _targets(
        self, project_id: UUID, scope: QueryScope, query: str, now: datetime
    ) -> int:
        if not scope:
            return 0
        rows = self._filtered(
            project_id, WEB, scope, query, now, columns=[Subdomain.target_id]
        ).statement.subquery()
        return int(
            await self.session.scalar(
                select(func.count(func.distinct(rows.c.target_id)))
            )
            or 0
        )
