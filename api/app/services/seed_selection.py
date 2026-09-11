"""Resolve a selection into the scans that run it."""

from __future__ import annotations

from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.asset_query import QueryScope
from app.services.endpoint import EndpointService
from app.services.ip_address import IpAddressService
from app.services.port import PortService
from app.services.subdomain import SubdomainService
from app.services.surface_scope import SurfaceScopeService
from app.services.vulnerability import VulnerabilityService
from shared.definitions.rescan import (
    MAX_RUN_ASSETS,
    MAX_RUN_SCANS,
    SeedKind,
    seed_kind_for,
)
from shared.definitions.surface import SurfaceDimension
from shared.models.endpoint import EndpointFilter
from shared.models.ip_address import IpAddress
from shared.models.scan import (
    ResolvedSelection,
    Scan,
    SeedGroup,
    SeedSelection,
)
from shared.models.scan_correlation import IpGroupFilter, ServiceFilter
from shared.models.subdomain import Subdomain, SubdomainFilter
from shared.models.target import Target
from shared.models.vulnerability import VulnerabilityFilter

FILTERS = {
    SurfaceDimension.WEB_ASSETS.value: SubdomainFilter,
    SurfaceDimension.ENDPOINTS.value: EndpointFilter,
    SurfaceDimension.SERVICES.value: ServiceFilter,
    SurfaceDimension.IPS.value: IpGroupFilter,
    SurfaceDimension.VULNERABILITIES.value: VulnerabilityFilter,
}

# one past the cap
_PROBE = MAX_RUN_ASSETS + 1


class SeedSelectionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.scopes = SurfaceScopeService(session)

    async def resolve(
        self, selection: SeedSelection, project_id: UUID
    ) -> ResolvedSelection:
        pairs = (
            await self._from_query(selection, project_id)
            if selection.query is not None
            else await self._from_picks(selection, project_id)
        )
        probed = len(pairs)
        excluded = {value.strip() for value in selection.exclude}
        by_scan: dict[UUID, list[str]] = {}
        seen: set[tuple[UUID, str]] = set()
        kept = 0
        for raw, scan_id in pairs:
            value = (raw or "").strip()
            if not value or value in excluded or (scan_id, value) in seen:
                continue
            if kept >= MAX_RUN_ASSETS:
                break
            seen.add((scan_id, value))
            by_scan.setdefault(scan_id, []).append(value)
            kept += 1

        groups, dropped = await self._groups(by_scan, project_id)
        overflowed = probed >= _PROBE
        return ResolvedSelection(
            groups=groups,
            total=sum(len(g.values) for g in groups),
            matched=None if overflowed else probed,
            capped=overflowed or probed > kept or dropped,
        )

    async def _from_picks(
        self, selection: SeedSelection, project_id: UUID
    ) -> list[tuple[str, UUID]]:
        named = [(p.value, p.scan_id) for p in selection.picks if p.scan_id is not None]
        loose = [p.value for p in selection.picks if p.scan_id is None]
        if not loose:
            return named
        return named + await self._locate(loose, selection.dimension, project_id)

    async def _locate(
        self, values: list[str], dimension: str, project_id: UUID
    ) -> list[tuple[str, UUID]]:
        """Resolve values to scans through the dimension scope."""
        scope = await self.scopes.scope(project_id, dimension)
        if not scope:
            return []
        model, column = (
            (IpAddress, IpAddress.ip)
            if seed_kind_for(dimension) == SeedKind.ADDRESS.value
            else (Subdomain, Subdomain.name)
        )
        rows = await self.session.execute(
            select(column, model.scan_id)
            .where(scope.match(model.scan_id), column.in_(values))
            .distinct()
        )
        return [(value, scan_id) for value, scan_id in rows.all()]

    async def _from_query(
        self, selection: SeedSelection, project_id: UUID
    ) -> list[tuple[str, UUID]]:
        query = selection.query
        dimension = selection.dimension
        scope = (
            QueryScope(tuple(query.scan_ids), project_id=project_id)
            if query.scan_ids
            else await self.scopes.scope(project_id, dimension)
        )
        if not scope:
            return []
        try:
            f = FILTERS[dimension].model_validate(query.filter)
        except ValidationError as exc:
            msg = f"Invalid {dimension} filter."
            raise ValueError(msg) from exc

        if dimension == SurfaceDimension.WEB_ASSETS.value:
            return await SubdomainService(self.session).seeds(
                project_id, scope, f, _PROBE
            )
        if dimension == SurfaceDimension.ENDPOINTS.value:
            return await EndpointService(self.session).seeds(scope, f, _PROBE)
        if dimension == SurfaceDimension.SERVICES.value:
            return await PortService(self.session).seeds(scope, f, _PROBE)
        if dimension == SurfaceDimension.VULNERABILITIES.value:
            return await VulnerabilityService(self.session).seeds(scope, f, _PROBE)
        return await self._addresses(scope, f, project_id, dimension)

    async def _addresses(
        self, scope: QueryScope, f, project_id: UUID, dimension: str
    ) -> list[tuple[str, UUID]]:
        rows = await IpAddressService(self.session).seeds(scope, f, _PROBE)
        by_target = await self.scopes.scans_by_target(project_id, dimension)
        out: list[tuple[str, UUID]] = []
        for ip, target_ids in rows:
            for target_id in target_ids:
                scan_id = by_target.get(target_id)
                if scan_id is not None:
                    out.append((ip, scan_id))
        return out

    async def _groups(
        self, by_scan: dict[UUID, list[str]], project_id: UUID
    ) -> tuple[list[SeedGroup], bool]:
        if not by_scan:
            return [], False
        rows = await self.session.execute(
            select(Scan.id, Scan.target_id, Target.target_value)
            .join(Target, Target.id == Scan.target_id)
            .where(Scan.id.in_(by_scan.keys()), Scan.project_id == project_id)
        )
        groups = [
            SeedGroup(
                scan_id=scan_id,
                target_id=target_id,
                target_value=target_value,
                values=by_scan[scan_id],
            )
            for scan_id, target_id, target_value in rows.all()
        ]
        groups.sort(key=lambda g: g.target_value)
        return groups[:MAX_RUN_SCANS], len(groups) > MAX_RUN_SCANS
