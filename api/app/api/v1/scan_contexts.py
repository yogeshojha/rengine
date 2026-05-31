from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from app.services.scan_context import ScanContextService
from shared.models.scan_context import (
    ScanContextCreate,
    ScanContextRead,
    ScanContextUpdate,
)

router = APIRouter(
    prefix="/contexts",
    tags=["scan-contexts"],
)


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ScanContextService:
    return ScanContextService(session)


@router.get("", response_model=list[ScanContextRead])
async def list_contexts(
    _current_user: CurrentUser,
    service: Annotated[ScanContextService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.list(project_id)


@router.post("", response_model=ScanContextRead, status_code=status.HTTP_201_CREATED)
async def create_context(
    data: ScanContextCreate,
    current_user: CurrentUser,
    service: Annotated[ScanContextService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.create(
        project_id=project_id,
        created_by=current_user.id,
        data=data,
    )


@router.get("/{id}", response_model=ScanContextRead)
async def get_context(
    id: UUID,
    _current_user: CurrentUser,
    service: Annotated[ScanContextService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.get(id=id, project_id=project_id)


@router.patch("/{id}", response_model=ScanContextRead)
async def update_context(
    id: UUID,
    data: ScanContextUpdate,
    _current_user: CurrentUser,
    service: Annotated[ScanContextService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.update(id=id, project_id=project_id, data=data)


@router.delete("/{id}", response_model=dict)
async def delete_context(
    id: UUID,
    _current_user: CurrentUser,
    service: Annotated[ScanContextService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    await service.delete(id=id, project_id=project_id)
    return {"deleted": True}


@router.post(
    "/{id}/duplicate",
    response_model=ScanContextRead,
    status_code=status.HTTP_201_CREATED,
)
async def duplicate_context(
    id: UUID,
    current_user: CurrentUser,
    service: Annotated[ScanContextService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.duplicate(
        id=id, project_id=project_id, created_by=current_user.id
    )
