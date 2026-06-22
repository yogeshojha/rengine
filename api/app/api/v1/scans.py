from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from app.services.scan import ScanService
from shared.enums.scan import ScanStatus
from shared.models.scan import ScanCreate, ScanRead, ScanStats
from shared.models.scan_preview import ScanPreview

router = APIRouter(
    prefix="/scans",
    tags=["scans"],
)


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ScanService:
    return ScanService(session)


@router.post("/preview", response_model=ScanPreview)
async def preview_scan(
    data: ScanCreate,
    _current_user: CurrentUser,
    service: Annotated[ScanService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.preview(data=data, project_id=project_id)


@router.post("", response_model=ScanRead, status_code=status.HTTP_201_CREATED)
async def create_scan(
    data: ScanCreate,
    current_user: CurrentUser,
    service: Annotated[ScanService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.create(
        data=data, project_id=project_id, created_by=current_user.id
    )


@router.get("", response_model=list[ScanRead])
async def list_scans(
    _current_user: CurrentUser,
    service: Annotated[ScanService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    target_id: Annotated[UUID | None, Query(description="Filter by target ID")] = None,
    status: Annotated[ScanStatus | None, Query(description="Filter by status")] = None,
    limit: Annotated[int, Query(ge=1, le=500, description="Max rows")] = 100,
    offset: Annotated[int, Query(ge=0, description="Rows to skip")] = 0,
):
    return await service.list(
        project_id=project_id,
        target_id=target_id,
        status=status.value if status else None,
        limit=limit,
        offset=offset,
    )


@router.get("/stats", response_model=ScanStats)
async def scan_stats(
    _current_user: CurrentUser,
    service: Annotated[ScanService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    target_id: Annotated[UUID | None, Query(description="Filter by target ID")] = None,
):
    return await service.stats(project_id=project_id, target_id=target_id)


@router.get("/{id}", response_model=ScanRead)
async def get_scan(
    id: UUID,
    _current_user: CurrentUser,
    service: Annotated[ScanService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.get(id=id, project_id=project_id)


@router.post("/{id}/cancel", response_model=ScanRead)
async def cancel_scan(
    id: UUID,
    _current_user: CurrentUser,
    service: Annotated[ScanService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.cancel(id=id, project_id=project_id)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scan(
    id: UUID,
    _current_user: CurrentUser,
    service: Annotated[ScanService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    await service.delete(id=id, project_id=project_id)
