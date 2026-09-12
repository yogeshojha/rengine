from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.api.scope import ServiceScope
from app.core.database import get_session
from app.services.asset_query import build_schema
from app.services.origin_exposure import OriginExposureService
from app.services.port import PortService
from shared.definitions.asset_query import SERVICE_QUERY
from shared.models.asset_query import QueryGroups, QueryLeads, QuerySchema
from shared.models.port import PortRead, PortSummary
from shared.models.scan_correlation import (
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


@router.get("", response_model=list[PortRead])
async def list_ports(
    _current_user: CurrentUser,
    service: Annotated[PortService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    scan_id: Annotated[UUID | None, Query(description="Filter by scan ID")] = None,
    target_id: Annotated[UUID | None, Query(description="Filter by target ID")] = None,
    search: Annotated[str | None, Query(description="Substring match on IP")] = None,
    limit: Annotated[int, Query(ge=1, le=1000, description="Max rows")] = 1000,
    offset: Annotated[int, Query(ge=0, description="Rows to skip")] = 0,
):
    return await service.list(
        project_id=project_id,
        scan_id=scan_id,
        target_id=target_id,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get("/summary", response_model=PortSummary)
async def port_summary(
    _current_user: CurrentUser,
    service: Annotated[PortService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    scan_id: Annotated[UUID | None, Query(description="Filter by scan ID")] = None,
    target_id: Annotated[UUID | None, Query(description="Filter by target ID")] = None,
):
    return await service.summary(
        project_id=project_id, scan_id=scan_id, target_id=target_id
    )


@router.get("/search/schema", response_model=QuerySchema)
async def service_query_schema(_current_user: CurrentUser):
    return build_schema(SERVICE_QUERY)


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
    )


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
