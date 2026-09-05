from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from app.services.asset_query import build_schema
from app.services.endpoint import EndpointService
from app.services.endpoint_structure import EndpointStructureService
from shared.definitions.asset_query import ENDPOINT_QUERY
from shared.models.asset_query import QueryGroups, QueryLeads, QuerySchema
from shared.models.endpoint import (
    CoverageRead,
    EndpointDetail,
    EndpointFacets,
    EndpointFilter,
    EndpointPage,
    EndpointSummary,
    EndpointTree,
    ScanStructure,
)

router = APIRouter(prefix="/endpoints", tags=["endpoints"])

_TREE_MODES = ("host", "merged")


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EndpointService:
    return EndpointService(session)


@router.get("/search/schema", response_model=QuerySchema)
async def endpoint_query_schema(_current_user: CurrentUser):
    return build_schema(ENDPOINT_QUERY)


@router.post("/search", response_model=EndpointPage)
async def search_endpoints(
    _current_user: CurrentUser,
    service: Annotated[EndpointService, Depends(get_service)],
    scan_id: Annotated[UUID, Query(description="Scan ID")],
    body: EndpointFilter,
):
    return await service.search(scan_id, body)


@router.post("/search/leads", response_model=QueryLeads)
async def endpoint_leads(
    _current_user: CurrentUser,
    service: Annotated[EndpointService, Depends(get_service)],
    scan_id: Annotated[UUID, Query(description="Scan ID")],
    body: EndpointFilter,
):
    return await service.leads(scan_id, body)


@router.post("/search/groups", response_model=QueryGroups)
async def endpoint_groups(
    _current_user: CurrentUser,
    service: Annotated[EndpointService, Depends(get_service)],
    scan_id: Annotated[UUID, Query(description="Scan ID")],
    group_by: Annotated[str, Query(description="Group dimension")],
    body: EndpointFilter,
):
    return await service.groups(scan_id, body, group_by)


@router.post("/tree", response_model=EndpointTree)
async def endpoint_tree(
    _current_user: CurrentUser,
    service: Annotated[EndpointService, Depends(get_service)],
    scan_id: Annotated[UUID, Query(description="Scan ID")],
    body: EndpointFilter,
    mode: Annotated[str, Query(description="host or merged")] = "host",
):
    resolved = mode if mode in _TREE_MODES else "host"
    return await service.tree(scan_id, body, resolved)


@router.get("/facets", response_model=EndpointFacets)
async def endpoint_facets(
    _current_user: CurrentUser,
    service: Annotated[EndpointService, Depends(get_service)],
    scan_id: Annotated[UUID, Query(description="Scan ID")],
    q: Annotated[str | None, Query(description="Query string")] = None,
):
    return await service.facets(scan_id, EndpointFilter(q=q))


@router.get("/summary", response_model=EndpointSummary)
async def endpoint_summary(
    _current_user: CurrentUser,
    service: Annotated[EndpointService, Depends(get_service)],
    scan_id: Annotated[UUID, Query(description="Scan ID")],
):
    return await service.summary(scan_id)


@router.get("/coverage", response_model=list[CoverageRead])
async def endpoint_coverage(
    _current_user: CurrentUser,
    service: Annotated[EndpointService, Depends(get_service)],
    scan_id: Annotated[UUID, Query(description="Scan ID")],
):
    return await service.coverage(scan_id)


@router.get("/structure", response_model=ScanStructure)
async def endpoint_structure(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    scan_id: Annotated[UUID, Query(description="Scan ID")],
):
    return await EndpointStructureService(session).build(scan_id)


@router.get("/{endpoint_id}", response_model=EndpointDetail)
async def get_endpoint(
    _current_user: CurrentUser,
    service: Annotated[EndpointService, Depends(get_service)],
    scan_id: Annotated[UUID, Query(description="Scan ID")],
    endpoint_id: Annotated[UUID, Path(description="Endpoint ID")],
):
    row = await service.detail(scan_id, endpoint_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint not found"
        )
    return row
