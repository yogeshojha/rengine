from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.api.scope import WebAssetScope
from app.core.database import get_session
from app.services.asset_query import build_schema
from app.services.correlation_graph import CorrelationGraphService
from app.services.hosting_flow import HostingFlowService
from app.services.related_domains import RelatedDomainService
from app.services.subdomain import SubdomainService
from shared.models.asset_query import (
    QueryCountRequest,
    QueryCounts,
    QueryGroups,
    QueryLeads,
    QuerySchema,
)
from shared.models.hosting_flow import HostingFlow
from shared.models.related import RelatedDomains
from shared.models.scan_correlation import (
    CorrelationGraph,
    SubdomainCorrelation,
    SubdomainInsights,
)
from shared.models.subdomain import (
    Facet,
    HygieneSummary,
    SubdomainFacets,
    SubdomainFilter,
    SubdomainRead,
    SubdomainRelation,
    SubdomainSearchResult,
    SubdomainSummary,
    TargetSubdomainRead,
)
from shared.services.asset_query import lead_cache

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
    scope: WebAssetScope,
):
    return await lead_cache.cached(
        service.session,
        name="search:web_assets",
        scans=scope.ids,
        facets=f"{project_id}|{body.model_dump_json()}",
        model=SubdomainSearchResult,
        build=lambda: service.search(project_id=project_id, scope=scope, f=body),
        ttl=lead_cache.SEARCH_TTL_SECONDS,
    )


@router.post("/search/counts", response_model=QueryCounts)
async def subdomain_search_counts(
    _current_user: CurrentUser,
    service: Annotated[SubdomainService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    scope: WebAssetScope,
    body: QueryCountRequest,
):
    return await service.counts(
        project_id=project_id, scope=scope, queries=body.queries
    )


@router.post("/search/leads", response_model=QueryLeads)
async def subdomain_search_leads(
    _current_user: CurrentUser,
    service: Annotated[SubdomainService, Depends(get_service)],
    body: SubdomainFilter,
    project_id: Annotated[UUID, Query(description="Project ID")],
    scope: WebAssetScope,
):
    return await service.leads(project_id=project_id, scope=scope, f=body)


@router.post("/search/groups", response_model=QueryGroups)
async def subdomain_search_groups(
    _current_user: CurrentUser,
    service: Annotated[SubdomainService, Depends(get_service)],
    body: SubdomainFilter,
    project_id: Annotated[UUID, Query(description="Project ID")],
    scope: WebAssetScope,
    group_by: Annotated[str, Query(max_length=20, description="Group dimension")],
):
    return await service.groups(
        project_id=project_id, scope=scope, f=body, key=group_by
    )


@router.get("/hosting-flow", response_model=HostingFlow)
async def subdomain_hosting_flow(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    scan_id: Annotated[UUID, Query(description="Scan ID")],
):
    return await lead_cache.cached(
        session,
        name="hosting_flow",
        scans=(scan_id,),
        facets=str(project_id),
        model=HostingFlow,
        build=lambda: HostingFlowService(session).for_scan(project_id, scan_id),
    )


@router.get("/correlation-graph", response_model=CorrelationGraph)
async def subdomain_correlation_graph(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    scan_id: Annotated[UUID, Query(description="Scan ID")],
):
    """Every identity two hosts of the scan share, as hubs the hosts hang off."""
    return await CorrelationGraphService(session).build(project_id, scan_id)


@router.get("/related-domains", response_model=RelatedDomains)
async def subdomain_related_domains(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    scan_id: Annotated[UUID, Query(description="Scan ID")],
):
    return await lead_cache.cached(
        session,
        name="related_domains",
        scans=(scan_id,),
        facets=str(project_id),
        model=RelatedDomains,
        build=lambda: RelatedDomainService(session).for_scan(
            project_id=project_id, scan_id=scan_id
        ),
    )


@router.get("/facets", response_model=SubdomainFacets)
async def subdomain_facets(
    _current_user: CurrentUser,
    service: Annotated[SubdomainService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    scope: WebAssetScope,
):
    return await lead_cache.cached(
        service.session,
        name="facets:web_assets",
        scans=scope.ids,
        facets=str(project_id),
        model=SubdomainFacets,
        build=lambda: service.facets(project_id=project_id, scope=scope),
    )


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
    return await lead_cache.cached(
        service.session,
        name="insights",
        scans=(scan_id,),
        facets=str(project_id),
        model=SubdomainInsights,
        build=lambda: service.insights(project_id=project_id, scan_id=scan_id),
    )


@router.get("/hygiene", response_model=HygieneSummary)
async def subdomain_hygiene(
    _current_user: CurrentUser,
    service: Annotated[SubdomainService, Depends(get_service)],
    scope: WebAssetScope,
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await lead_cache.cached(
        service.session,
        name="hygiene",
        scans=scope.ids,
        facets=str(project_id),
        model=HygieneSummary,
        build=lambda: service.hygiene(project_id=project_id, scope=scope),
    )


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
