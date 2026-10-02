from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.api.scope import IpScope
from app.core.database import get_session
from app.services.ip_address import IpAddressService
from shared.models.asset_query import QueryCounts, QueryGroups, QueryLeads
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
        live_ttl=None,
    )


@router.post("/search/tabs", response_model=QueryCounts)
async def ip_search_tabs(
    _current_user: CurrentUser,
    service: Annotated[IpAddressService, Depends(get_service)],
    scope: IpScope,
    body: IpGroupFilter,
):
    return await service.tabs(scope=scope, f=body)


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
