from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from app.services.asset_query import build_schema
from app.services.subdomain import SubdomainService
from shared.models.asset_query import QueryLeads, QuerySchema
from shared.models.scan_correlation import SubdomainCorrelation, SubdomainInsights
from shared.models.subdomain import (
    Facet,
    SubdomainFacets,
    SubdomainFilter,
    SubdomainRead,
    SubdomainRelation,
    SubdomainSearchResult,
    SubdomainSummary,
    TargetSubdomainRead,
)

router = APIRouter(
    prefix="/subdomains",
    tags=["subdomains"],
)


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SubdomainService:
    return SubdomainService(session)


@router.get("", response_model=list[SubdomainRead])
async def list_subdomains(
    _current_user: CurrentUser,
    service: Annotated[SubdomainService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    scan_id: Annotated[UUID | None, Query(description="Filter by scan ID")] = None,
    target_id: Annotated[UUID | None, Query(description="Filter by target ID")] = None,
    active_only: Annotated[
        bool, Query(description="Only resolving subdomains")
    ] = False,
    search: Annotated[str | None, Query(description="Substring match on name")] = None,
    limit: Annotated[int, Query(ge=1, le=1000, description="Max rows")] = 100,
    offset: Annotated[int, Query(ge=0, description="Rows to skip")] = 0,
):
    return await service.list(
        project_id=project_id,
        scan_id=scan_id,
        target_id=target_id,
        active_only=active_only,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get("/search/schema", response_model=QuerySchema)
async def subdomain_search_schema(_current_user: CurrentUser) -> QuerySchema:
    return build_schema()


@router.post("/search", response_model=SubdomainSearchResult)
async def search_subdomains(
    _current_user: CurrentUser,
    service: Annotated[SubdomainService, Depends(get_service)],
    body: SubdomainFilter,
    project_id: Annotated[UUID, Query(description="Project ID")],
    scan_id: Annotated[UUID, Query(description="Scan ID")],
):
    return await service.search(project_id=project_id, scan_id=scan_id, f=body)


@router.post("/search/leads", response_model=QueryLeads)
async def subdomain_search_leads(
    _current_user: CurrentUser,
    service: Annotated[SubdomainService, Depends(get_service)],
    body: SubdomainFilter,
    project_id: Annotated[UUID, Query(description="Project ID")],
    scan_id: Annotated[UUID, Query(description="Scan ID")],
):
    return await service.leads(project_id=project_id, scan_id=scan_id, f=body)


@router.get("/facets", response_model=SubdomainFacets)
async def subdomain_facets(
    _current_user: CurrentUser,
    service: Annotated[SubdomainService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    scan_id: Annotated[UUID, Query(description="Scan ID")],
):
    return await service.facets(project_id=project_id, scan_id=scan_id)


@router.get("/related", response_model=list[SubdomainRelation])
async def subdomain_related(
    _current_user: CurrentUser,
    service: Annotated[SubdomainService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    scan_id: Annotated[UUID, Query(description="Scan ID")],
    name: Annotated[str, Query(description="Subdomain name")],
):
    return await service.related(project_id=project_id, scan_id=scan_id, name=name)


@router.get("/tech", response_model=list[Facet])
async def subdomain_tech(
    _current_user: CurrentUser,
    service: Annotated[SubdomainService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    scan_id: Annotated[UUID, Query(description="Scan ID")],
    search: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
):
    return await service.tech(project_id, scan_id, search, limit)


@router.get("/insights", response_model=SubdomainInsights)
async def subdomain_insights(
    _current_user: CurrentUser,
    service: Annotated[SubdomainService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    scan_id: Annotated[UUID, Query(description="Scan ID")],
):
    return await service.insights(project_id=project_id, scan_id=scan_id)


@router.get("/correlation", response_model=SubdomainCorrelation)
async def subdomain_correlation(
    _current_user: CurrentUser,
    service: Annotated[SubdomainService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    scan_id: Annotated[UUID, Query(description="Scan ID")],
    name: Annotated[str, Query(description="Subdomain name")],
):
    return await service.correlation(project_id=project_id, scan_id=scan_id, name=name)


@router.get("/summary", response_model=SubdomainSummary)
async def subdomain_summary(
    _current_user: CurrentUser,
    service: Annotated[SubdomainService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    scan_id: Annotated[UUID | None, Query(description="Filter by scan ID")] = None,
    target_id: Annotated[UUID | None, Query(description="Filter by target ID")] = None,
):
    return await service.summary(
        project_id=project_id, scan_id=scan_id, target_id=target_id
    )


@router.get("/rollup", response_model=list[TargetSubdomainRead])
async def target_subdomain_rollup(
    _current_user: CurrentUser,
    service: Annotated[SubdomainService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    target_id: Annotated[UUID, Query(description="Target ID")],
    active_only: Annotated[
        bool, Query(description="Only resolving subdomains")
    ] = False,
    search: Annotated[str | None, Query(description="Substring match on name")] = None,
    limit: Annotated[int, Query(ge=1, le=1000, description="Max rows")] = 100,
    offset: Annotated[int, Query(ge=0, description="Rows to skip")] = 0,
):
    return await service.list_for_target(
        project_id=project_id,
        target_id=target_id,
        active_only=active_only,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get("/rollup/summary", response_model=SubdomainSummary)
async def target_subdomain_rollup_summary(
    _current_user: CurrentUser,
    service: Annotated[SubdomainService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    target_id: Annotated[UUID, Query(description="Target ID")],
):
    return await service.summary_for_target(project_id=project_id, target_id=target_id)
