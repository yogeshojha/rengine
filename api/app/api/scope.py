"""Result view scope: one scan, or every target's latest covering scan."""

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.services.asset_query import QueryScope
from app.services.surface_scope import SurfaceScopeService
from app.services.target_scope import TargetFilter, resolve_targets
from shared.definitions.surface import SurfaceDimension

_MISSING = "Pass scan_id for one run, or project_id for the whole project."


def target_filter(
    target_id: Annotated[
        list[UUID] | None, Query(description="Only these targets")
    ] = None,
    organization_id: Annotated[
        UUID | None, Query(description="Only targets of this organization")
    ] = None,
    tag_id: Annotated[
        UUID | None, Query(description="Only targets with this tag")
    ] = None,
) -> TargetFilter:
    return TargetFilter(tuple(target_id or ()), organization_id, tag_id)


TargetFilterDep = Annotated[TargetFilter, Depends(target_filter)]


async def resolve_scope(
    session: AsyncSession,
    dimension: str,
    scan_id: UUID | None,
    project_id: UUID | None,
    spec: TargetFilter | None = None,
) -> QueryScope:
    if scan_id is not None:
        return QueryScope((scan_id,), project_id=project_id)
    if project_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=_MISSING
        )
    targets = await resolve_targets(session, project_id, spec)
    return await SurfaceScopeService(session).scope(
        project_id, dimension, targets=targets
    )


def scope_for(dimension: SurfaceDimension) -> Callable:
    async def resolve(
        session: Annotated[AsyncSession, Depends(get_session)],
        spec: TargetFilterDep,
        scan_id: Annotated[UUID | None, Query(description="Scan ID")] = None,
        project_id: Annotated[UUID | None, Query(description="Project ID")] = None,
    ) -> QueryScope:
        return await resolve_scope(session, dimension.value, scan_id, project_id, spec)

    return resolve


WebAssetScope = Annotated[QueryScope, Depends(scope_for(SurfaceDimension.WEB_ASSETS))]
EndpointScope = Annotated[QueryScope, Depends(scope_for(SurfaceDimension.ENDPOINTS))]
ServiceScope = Annotated[QueryScope, Depends(scope_for(SurfaceDimension.SERVICES))]
IpScope = Annotated[QueryScope, Depends(scope_for(SurfaceDimension.IPS))]
VulnScope = Annotated[QueryScope, Depends(scope_for(SurfaceDimension.VULNERABILITIES))]
SoftwareScope = Annotated[QueryScope, Depends(scope_for(SurfaceDimension.SOFTWARE))]
SecretScope = Annotated[QueryScope, Depends(scope_for(SurfaceDimension.SECRETS))]
