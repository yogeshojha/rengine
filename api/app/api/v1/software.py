from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.api.scope import SoftwareScope
from app.core.database import get_session
from app.services.asset_query import build_schema
from app.services.software import SoftwareService
from shared.definitions.asset_query import SOFTWARE_QUERY
from shared.models.asset_query import QuerySchema
from shared.models.software import (
    SoftwareCoverage,
    SoftwareFacets,
    SoftwareFilter,
    SoftwarePage,
)
from shared.services.asset_query import lead_cache

router = APIRouter(prefix="/software", tags=["software"])

MAX_COUNT_QUERIES = 25


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SoftwareService:
    return SoftwareService(session)


@router.get("/search/schema", response_model=QuerySchema)
async def software_schema(_current_user: CurrentUser):
    return build_schema(SOFTWARE_QUERY)


@router.post("/search", response_model=SoftwarePage)
async def search_software(
    _current_user: CurrentUser,
    service: Annotated[SoftwareService, Depends(get_service)],
    scope: SoftwareScope,
    body: SoftwareFilter,
):
    return await lead_cache.cached(
        service.session,
        name="search:software",
        scans=scope.ids,
        facets=body.model_dump_json(),
        model=SoftwarePage,
        build=lambda: service.search(scope, body),
        keep=lambda page: page.error is None,
    )


@router.get("/facets", response_model=SoftwareFacets)
async def software_facets(
    _current_user: CurrentUser,
    service: Annotated[SoftwareService, Depends(get_service)],
    scope: SoftwareScope,
):
    return await service.facets(scope)


@router.get("/coverage", response_model=SoftwareCoverage)
async def software_coverage(
    _current_user: CurrentUser,
    service: Annotated[SoftwareService, Depends(get_service)],
    scope: SoftwareScope,
):
    return await service.coverage(scope)


@router.post("/search/counts", response_model=dict[str, int])
async def software_counts(
    _current_user: CurrentUser,
    service: Annotated[SoftwareService, Depends(get_service)],
    scope: SoftwareScope,
    queries: Annotated[list[str], Body(embed=True, max_length=MAX_COUNT_QUERIES)],
):
    return await service.counts(scope, queries)


@router.get("/total", response_model=int)
async def software_total(
    _current_user: CurrentUser,
    service: Annotated[SoftwareService, Depends(get_service)],
    scan_id: Annotated[UUID, Query(description="Scan ID")],
):
    return await service.scan_total(scan_id)
