from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.access import ProjectId
from app.api.deps import CurrentUser
from app.core.database import get_session
from app.services.cloud_storage import CloudStorageService
from app.services.target_scope import require_scan, require_target
from shared.models.cloud_storage import CloudBucketSummary, CloudBucketTriageUpdate

router = APIRouter(prefix="/cloud-storage", tags=["cloud-storage"])


class TriageResult(BaseModel):
    updated: int


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CloudStorageService:
    return CloudStorageService(session)


@router.get("", response_model=CloudBucketSummary)
async def scan_cloud_storage(
    _current_user: CurrentUser,
    service: Annotated[CloudStorageService, Depends(get_service)],
    project_id: ProjectId,
    scan_id: Annotated[UUID, Query(description="Scan ID")],
):
    """Cloud buckets of one scan."""
    await require_scan(service.session, project_id, scan_id)
    return await service.for_scan(project_id, scan_id)


@router.get("/target/{target_id}", response_model=CloudBucketSummary)
async def target_cloud_storage(
    _current_user: CurrentUser,
    service: Annotated[CloudStorageService, Depends(get_service)],
    target_id: UUID,
    project_id: ProjectId,
):
    """The target's newest settled run that checked cloud storage."""
    await require_target(service.session, project_id, target_id)
    return await service.for_target(project_id, target_id)


@router.patch("/triage", response_model=TriageResult)
async def triage_cloud_storage(
    _current_user: CurrentUser,
    service: Annotated[CloudStorageService, Depends(get_service)],
    body: CloudBucketTriageUpdate,
    project_id: ProjectId,
):
    """Set the review state of cloud buckets of one target."""
    await require_target(service.session, project_id, body.target_id)
    updated = await service.triage(
        project_id, body.target_id, body.buckets, body.state.value
    )
    return TriageResult(updated=updated)
