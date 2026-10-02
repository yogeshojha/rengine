from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.api.scope import ServiceScope
from app.core.database import get_session
from app.services.origin_exposure import OriginExposureService
from app.services.port import PortService
from shared.models.asset_query import QueryCounts, QueryGroups, QueryLeads
from shared.models.scan_correlation import (
    AiSummary,
    OriginExposure,
    ScanExposure,
    ServiceFacets,
    ServiceFilter,
    ServicePage,
)
from shared.services.asset_query import lead_cache

router = APIRouter(
    prefix="/ports",
    tags=["ports"],
)


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PortService:
    return PortService(session)


@router.post("/search", response_model=ServicePage)
async def search_services(
    _current_user: CurrentUser,
    service: Annotated[PortService, Depends(get_service)],
    scope: ServiceScope,
    body: ServiceFilter,
):
    return await lead_cache.cached(
        service.session,
        name="search:services",
        scans=scope.ids,
        facets=body.model_dump_json(),
        model=ServicePage,
        build=lambda: service.search(scope, body),
        ttl=lead_cache.SEARCH_TTL_SECONDS,
        live_ttl=None,
    )


@router.post("/search/tabs", response_model=QueryCounts)
async def service_tabs(
    _current_user: CurrentUser,
    service: Annotated[PortService, Depends(get_service)],
    scope: ServiceScope,
    body: ServiceFilter,
):
    return await service.tabs(scope, body)


@router.post("/search/leads", response_model=QueryLeads)
async def service_leads(
    _current_user: CurrentUser,
    service: Annotated[PortService, Depends(get_service)],
    scope: ServiceScope,
    body: ServiceFilter,
):
    return await service.leads(scope, body)


@router.post("/search/groups", response_model=QueryGroups)
async def service_groups(
    _current_user: CurrentUser,
    service: Annotated[PortService, Depends(get_service)],
    scope: ServiceScope,
    group_by: Annotated[str, Query(description="Group dimension key", max_length=40)],
    body: ServiceFilter,
):
    return await service.groups(scope, body, group_by)


@router.get("/facets", response_model=ServiceFacets)
async def service_facets(
    _current_user: CurrentUser,
    service: Annotated[PortService, Depends(get_service)],
    scope: ServiceScope,
):
    return await lead_cache.cached(
        service.session,
        name="facets:services",
        scans=scope.ids,
        facets="",
        model=ServiceFacets,
        build=lambda: service.facets(scope),
    )


@router.get("/ai", response_model=AiSummary)
async def service_ai(
    _current_user: CurrentUser,
    service: Annotated[PortService, Depends(get_service)],
    scope: ServiceScope,
):
    """Services carrying each AI service, and the models those services listed."""
    return await lead_cache.cached(
        service.session,
        name="ai:services",
        scans=scope.ids,
        facets="",
        model=AiSummary,
        build=lambda: service.ai(scope),
    )


@router.get("/origins", response_model=OriginExposure)
async def origin_exposure(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    scan_id: Annotated[UUID, Query(description="Scan ID")],
):
    return await lead_cache.cached(
        session,
        name="origins",
        scans=(scan_id,),
        facets="",
        model=OriginExposure,
        build=lambda: OriginExposureService(session).run(scan_id),
    )


@router.get("/exposure", response_model=ScanExposure)
async def scan_exposure(
    _current_user: CurrentUser,
    service: Annotated[PortService, Depends(get_service)],
    scope: ServiceScope,
):
    return await lead_cache.cached(
        service.session,
        name="exposure",
        scans=scope.ids,
        facets="",
        model=ScanExposure,
        build=lambda: service.exposure(scope),
    )
