from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.api.scope import IpScope
from app.core.database import get_session
from app.services.asset_query import build_schema
from app.services.ip_address import IpAddressService
from shared.definitions.asset_query import IP_QUERY
from shared.models.asset_query import QueryGroups, QueryLeads, QuerySchema
from shared.models.ip_address import IpAddressRead, IpAddressSummary
from shared.models.scan_correlation import IpFacets, IpGroupFilter, IpGroupPage
from shared.services.asset_query import lead_cache

router = APIRouter(
    prefix="/ips",
    tags=["ips"],
)


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> IpAddressService:
    return IpAddressService(session)


@router.get("", response_model=list[IpAddressRead])
async def list_ips(
    _current_user: CurrentUser,
    service: Annotated[IpAddressService, Depends(get_service)],
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


@router.get("/search/schema", response_model=QuerySchema)
async def ip_search_schema(_current_user: CurrentUser) -> QuerySchema:
    return build_schema(IP_QUERY)


@router.post("/search", response_model=IpGroupPage)
async def ip_search(
    _current_user: CurrentUser,
    service: Annotated[IpAddressService, Depends(get_service)],
    scope: IpScope,
    body: IpGroupFilter,
):
    return await lead_cache.cached(
        service.session,
        name="search:ips",
        scans=scope.ids,
        facets=body.model_dump_json(),
        model=IpGroupPage,
        build=lambda: service.search(scope=scope, f=body),
        ttl=lead_cache.SEARCH_TTL_SECONDS,
    )


@router.post("/search/leads", response_model=QueryLeads)
async def ip_search_leads(
    _current_user: CurrentUser,
    service: Annotated[IpAddressService, Depends(get_service)],
    scope: IpScope,
    body: IpGroupFilter,
):
    return await service.leads(scope=scope, f=body)


@router.post("/search/groups", response_model=QueryGroups)
async def ip_search_groups(
    _current_user: CurrentUser,
    service: Annotated[IpAddressService, Depends(get_service)],
    scope: IpScope,
    group_by: Annotated[str, Query(max_length=40, description="Group dimension")],
    body: IpGroupFilter,
):
    return await service.groups(scope=scope, f=body, key=group_by)


@router.get("/facets", response_model=IpFacets)
async def ip_facets(
    _current_user: CurrentUser,
    service: Annotated[IpAddressService, Depends(get_service)],
    scope: IpScope,
):
    return await lead_cache.cached(
        service.session,
        name="facets:ips",
        scans=scope.ids,
        facets="",
        model=IpFacets,
        build=lambda: service.facets(scope=scope),
    )


@router.get("/summary", response_model=IpAddressSummary)
async def ip_summary(
    _current_user: CurrentUser,
    service: Annotated[IpAddressService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    scan_id: Annotated[UUID | None, Query(description="Filter by scan ID")] = None,
    target_id: Annotated[UUID | None, Query(description="Filter by target ID")] = None,
):
    return await service.summary(
        project_id=project_id, scan_id=scan_id, target_id=target_id
    )
