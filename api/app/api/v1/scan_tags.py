from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from app.services.scan_tags import ScanTagService
from shared.models.scan_tag import (
    ScanTagAssignment,
    ScanTagChange,
    ScanTagRead,
)

router = APIRouter(prefix="/scan-tags", tags=["scan-tags"])


def get_service(session: Annotated[AsyncSession, Depends(get_session)]):
    return ScanTagService(session)


@router.get("", response_model=list[ScanTagRead])
async def list_scan_tags(
    _current_user: CurrentUser,
    service: Annotated[ScanTagService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.for_project(project_id)


@router.post("/assign", response_model=list[ScanTagAssignment])
async def assign_scan_tags(
    data: ScanTagChange,
    current_user: CurrentUser,
    service: Annotated[ScanTagService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.change(
        project_id, data.scan_ids, data.add, data.remove, current_user.id
    )
