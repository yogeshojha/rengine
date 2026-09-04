from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from app.services.asset_query import build_schema
from app.services.vulnerability import VulnerabilityService
from shared.definitions.asset_query import VULN_QUERY
from shared.definitions.vulnerabilities import VULN_STATES
from shared.models.asset_query import QueryGroups, QueryLeads, QuerySchema
from shared.models.vulnerability import (
    BulkTriageResult,
    BulkTriageUpdate,
    CoverageRead,
    IssuePage,
    ScanVulnerabilities,
    TriageResult,
    TriageUpdate,
    VulnerabilityFacets,
    VulnerabilityFilter,
    VulnerabilityPage,
    VulnerabilityRead,
)

router = APIRouter(prefix="/vulnerabilities", tags=["vulnerabilities"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> VulnerabilityService:
    return VulnerabilityService(session)


@router.get("/search/schema", response_model=QuerySchema)
async def vulnerability_query_schema(_current_user: CurrentUser):
    return build_schema(VULN_QUERY)


@router.post("/search", response_model=VulnerabilityPage)
async def search_vulnerabilities(
    _current_user: CurrentUser,
    service: Annotated[VulnerabilityService, Depends(get_service)],
    scan_id: Annotated[UUID, Query(description="Scan ID")],
    body: VulnerabilityFilter,
):
    return await service.search(scan_id, body)


@router.post("/search/issues", response_model=IssuePage)
async def search_issues(
    _current_user: CurrentUser,
    service: Annotated[VulnerabilityService, Depends(get_service)],
    scan_id: Annotated[UUID, Query(description="Scan ID")],
    body: VulnerabilityFilter,
):
    return await service.issues(scan_id, body)


@router.post("/search/leads", response_model=QueryLeads)
async def vulnerability_leads(
    _current_user: CurrentUser,
    service: Annotated[VulnerabilityService, Depends(get_service)],
    scan_id: Annotated[UUID, Query(description="Scan ID")],
    body: VulnerabilityFilter,
):
    return await service.leads(scan_id, body)


@router.post("/search/groups", response_model=QueryGroups)
async def vulnerability_groups(
    _current_user: CurrentUser,
    service: Annotated[VulnerabilityService, Depends(get_service)],
    scan_id: Annotated[UUID, Query(description="Scan ID")],
    group_by: Annotated[str, Query(description="Group dimension key", max_length=40)],
    body: VulnerabilityFilter,
):
    return await service.groups(scan_id, body, group_by)


@router.get("/facets", response_model=VulnerabilityFacets)
async def vulnerability_facets(
    _current_user: CurrentUser,
    service: Annotated[VulnerabilityService, Depends(get_service)],
    scan_id: Annotated[UUID, Query(description="Scan ID")],
):
    return await service.facets(scan_id)


@router.get("/overview", response_model=ScanVulnerabilities)
async def vulnerability_overview(
    _current_user: CurrentUser,
    service: Annotated[VulnerabilityService, Depends(get_service)],
    scan_id: Annotated[UUID, Query(description="Scan ID")],
):
    return await service.overview(scan_id)


@router.get("/coverage", response_model=list[CoverageRead])
async def vulnerability_coverage(
    _current_user: CurrentUser,
    service: Annotated[VulnerabilityService, Depends(get_service)],
    scan_id: Annotated[UUID, Query(description="Scan ID")],
):
    return await service.coverage(scan_id)


@router.get("/{vulnerability_id}", response_model=VulnerabilityRead)
async def get_vulnerability(
    _current_user: CurrentUser,
    service: Annotated[VulnerabilityService, Depends(get_service)],
    vulnerability_id: Annotated[UUID, Path(description="Vulnerability ID")],
    scan_id: Annotated[UUID, Query(description="Scan ID")],
):
    found = await service.get(scan_id, vulnerability_id)
    if found is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found"
        )
    return found


@router.post("/triage/bulk", response_model=BulkTriageResult)
async def triage_many(
    current_user: CurrentUser,
    service: Annotated[VulnerabilityService, Depends(get_service)],
    scan_id: Annotated[UUID, Query(description="Scan ID")],
    body: BulkTriageUpdate,
):
    if body.state not in VULN_STATES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown state"
        )
    return await service.triage_many(scan_id, body, current_user.id)


@router.patch("/triage/{fingerprint}", response_model=TriageResult)
async def triage_vulnerability(
    current_user: CurrentUser,
    service: Annotated[VulnerabilityService, Depends(get_service)],
    fingerprint: Annotated[str, Path(description="Finding fingerprint", max_length=64)],
    scan_id: Annotated[UUID, Query(description="Scan ID")],
    body: TriageUpdate,
):
    result = await service.triage(scan_id, fingerprint, body, current_user.id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found"
        )
    return result
