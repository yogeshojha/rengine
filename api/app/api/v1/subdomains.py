from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from app.services.subdomain import SubdomainService
from shared.models.subdomain import (
    SubdomainRead,
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
