import re
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from app.services.cve_exposure import DEFAULT_PAGE_SIZE, CveExposureService
from shared.models.cve_exposure import CveExposure, CveIndex

router = APIRouter(prefix="/cves", tags=["cves"])

CVE_PATTERN = re.compile(r"^CVE-\d{4}-\d{4,7}$", re.IGNORECASE)
MAX_QUERY = 40


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CveExposureService:
    return CveExposureService(session)


@router.get("", response_model=CveIndex)
async def list_cves(
    _current_user: CurrentUser,
    service: Annotated[CveExposureService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    q: Annotated[str, Query(max_length=MAX_QUERY, description="CVE filter")] = "",
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=200)] = DEFAULT_PAGE_SIZE,
    sort: Annotated[str, Query(description="Sort key")] = "rank",
    dir: Annotated[
        str, Query(pattern="^(asc|desc)$", description="Sort direction")
    ] = "desc",
    severity: Annotated[str | None, Query(description="Severity")] = None,
    kev: Annotated[bool, Query(description="On the CISA KEV list")] = False,
    ransomware: Annotated[bool, Query(description="Used by ransomware")] = False,
    evidence: Annotated[list[str], Query(description="Evidence rung")] = [],  # noqa: B006
):
    return await service.index(
        project_id,
        q,
        page=page,
        size=size,
        sort=sort,
        direction=dir,
        severity=severity,
        kev=kev,
        ransomware=ransomware,
        evidence=evidence,
    )


@router.get("/{cve}", response_model=CveExposure)
async def cve_exposure(
    _current_user: CurrentUser,
    service: Annotated[CveExposureService, Depends(get_service)],
    cve: Annotated[str, Path(max_length=30)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    cleaned = cve.strip().upper()
    if not CVE_PATTERN.match(cleaned):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{cve} is not a CVE identifier.",
        )
    return await service.exposure(project_id, cleaned)
