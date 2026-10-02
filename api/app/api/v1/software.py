from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.api.scope import SoftwareScope
from app.core.database import get_session
from app.services.software import SoftwareService
from shared.models.asset_query import QueryCountRequest, QueryCounts
from shared.models.software import (
    SoftwareCoverage,
    SoftwareFacets,
    SoftwareFilter,
    SoftwarePage,
)
from shared.services.asset_query import lead_cache

router = APIRouter(prefix="/software", tags=["software"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SoftwareService:
    return SoftwareService(session)


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
        live_ttl=None,
    )


@router.post("/search/counts", response_model=QueryCounts)
async def software_search_counts(
    _current_user: CurrentUser,
    service: Annotated[SoftwareService, Depends(get_service)],
    scope: SoftwareScope,
    body: QueryCountRequest,
):
    return await service.counts(scope, body.queries)


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
