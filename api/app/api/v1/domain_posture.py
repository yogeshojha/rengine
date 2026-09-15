from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.api.scope import WebAssetScope
from app.core.database import get_session
from app.services.domain_posture import DomainPostureService
from shared.models.domain_posture import DomainPostureSummary
from shared.services.asset_query import lead_cache

router = APIRouter(prefix="/domain-posture", tags=["domain-posture"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DomainPostureService:
    return DomainPostureService(session)


@router.get("", response_model=DomainPostureSummary)
async def domain_posture(
    _current_user: CurrentUser,
    service: Annotated[DomainPostureService, Depends(get_service)],
    scope: WebAssetScope,
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    """Zones of one scan, with each check's count."""
    return await lead_cache.cached(
        service.session,
        name="domain_posture",
        scans=scope.ids,
        facets=str(project_id),
        model=DomainPostureSummary,
        build=lambda: service.summary(project_id=project_id, scope=scope),
    )


@router.get("/project", response_model=DomainPostureSummary)
async def project_domain_posture(
    _current_user: CurrentUser,
    service: Annotated[DomainPostureService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    """Every target's newest settled run."""
    return await service.for_project(project_id)


@router.get("/target/{target_id}", response_model=DomainPostureSummary)
async def target_domain_posture(
    _current_user: CurrentUser,
    service: Annotated[DomainPostureService, Depends(get_service)],
    target_id: UUID,
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    """The target's newest settled run that checked its zones."""
    return await service.for_target(project_id=project_id, target_id=target_id)
