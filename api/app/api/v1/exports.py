from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.access import ProjectId
from app.api.deps import CurrentUser
from app.core.database import get_session
from app.services.export import ExportService
from shared.definitions.exports import (
    BUNDLE_EXTENSION,
    BUNDLE_MEDIA_TYPE,
    FORMAT_MEDIA_TYPES,
)
from shared.models.export import ExportCreate, ExportRead

router = APIRouter(prefix="/exports", tags=["exports"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ExportService:
    return ExportService(session)


@router.post(
    "",
    summary="Start an export",
    response_model=ExportRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_export(
    data: ExportCreate,
    current_user: CurrentUser,
    service: Annotated[ExportService, Depends(get_service)],
    project_id: ProjectId,
):
    return await service.create(data, project_id, current_user.id)


@router.get("", summary="Exports of a project", response_model=list[ExportRead])
async def list_exports(
    _current_user: CurrentUser,
    service: Annotated[ExportService, Depends(get_service)],
    project_id: ProjectId,
    scan_id: Annotated[UUID | None, Query(description="One run")] = None,
    target_id: Annotated[UUID | None, Query(description="One target")] = None,
):
    return await service.list(project_id, scan_id, target_id)


@router.get(
    "/{export_id}", summary="One export and its status", response_model=ExportRead
)
async def get_export(
    export_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[ExportService, Depends(get_service)],
    project_id: ProjectId,
):
    return await service.get(export_id, project_id)


@router.post(
    "/{export_id}/rerun",
    response_model=ExportRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def rerun_export(
    export_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[ExportService, Depends(get_service)],
    project_id: ProjectId,
):
    return await service.rerun(export_id, project_id)


@router.get("/{export_id}/download", summary="Download an export file")
async def download_export(
    export_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[ExportService, Depends(get_service)],
    project_id: ProjectId,
):
    path, filename = await service.file_path(export_id, project_id)
    media = (
        BUNDLE_MEDIA_TYPE
        if filename.endswith(BUNDLE_EXTENSION)
        else FORMAT_MEDIA_TYPES.get(path.suffix.lstrip("."), "application/octet-stream")
    )
    return FileResponse(path, media_type=media, filename=filename)


@router.delete("/{export_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_export(
    export_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[ExportService, Depends(get_service)],
    project_id: ProjectId,
):
    await service.delete(export_id, project_id)
