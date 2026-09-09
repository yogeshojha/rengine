from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.api.scope import VulnScope
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
    scope: VulnScope,
    body: VulnerabilityFilter,
):
    return await service.search(scope, body)


@router.post("/search/issues", response_model=IssuePage)
async def search_issues(
    _current_user: CurrentUser,
    service: Annotated[VulnerabilityService, Depends(get_service)],
    scope: VulnScope,
    body: VulnerabilityFilter,
):
    return await service.issues(scope, body)


@router.post("/search/leads", response_model=QueryLeads)
async def vulnerability_leads(
    _current_user: CurrentUser,
    service: Annotated[VulnerabilityService, Depends(get_service)],
    scope: VulnScope,
    body: VulnerabilityFilter,
):
    return await service.leads(scope, body)


@router.post("/search/groups", response_model=QueryGroups)
async def vulnerability_groups(
    _current_user: CurrentUser,
    service: Annotated[VulnerabilityService, Depends(get_service)],
    scope: VulnScope,
    group_by: Annotated[str, Query(description="Group dimension key", max_length=40)],
    body: VulnerabilityFilter,
):
    return await service.groups(scope, body, group_by)


@router.get("/facets", response_model=VulnerabilityFacets)
async def vulnerability_facets(
    _current_user: CurrentUser,
    service: Annotated[VulnerabilityService, Depends(get_service)],
    scope: VulnScope,
):
    return await service.facets(scope)


@router.get("/overview", response_model=ScanVulnerabilities)
async def vulnerability_overview(
    _current_user: CurrentUser,
    service: Annotated[VulnerabilityService, Depends(get_service)],
    scope: VulnScope,
):
    return await service.overview(scope)


@router.get("/coverage", response_model=list[CoverageRead])
async def vulnerability_coverage(
    _current_user: CurrentUser,
    service: Annotated[VulnerabilityService, Depends(get_service)],
    scope: VulnScope,
):
    return await service.coverage(scope)


@router.get("/{vulnerability_id}", response_model=VulnerabilityRead)
async def get_vulnerability(
    _current_user: CurrentUser,
    service: Annotated[VulnerabilityService, Depends(get_service)],
    vulnerability_id: Annotated[UUID, Path(description="Vulnerability ID")],
    scope: VulnScope,
):
    found = await service.get(scope, vulnerability_id)
    if found is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found"
        )
    return found


@router.post("/triage/bulk", response_model=BulkTriageResult)
async def triage_many(
    current_user: CurrentUser,
    service: Annotated[VulnerabilityService, Depends(get_service)],
    scope: VulnScope,
    body: BulkTriageUpdate,
):
    if body.state not in VULN_STATES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown review state '{body.state}'. Expected one of "
            f"{', '.join(sorted(VULN_STATES))}.",
        )
    return await service.triage_many(scope, body, current_user.id)


@router.patch("/triage/{fingerprint}", response_model=TriageResult)
async def triage_vulnerability(
    current_user: CurrentUser,
    service: Annotated[VulnerabilityService, Depends(get_service)],
    fingerprint: Annotated[str, Path(description="Finding fingerprint", max_length=64)],
    scope: VulnScope,
    body: TriageUpdate,
):
    result = await service.triage(scope, fingerprint, body, current_user.id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found"
        )
    return result
