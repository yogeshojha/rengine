from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.api.pagination import Page
from app.core.database import get_session
from app.services.note import NoteService
from shared.models.note import NoteCount, NoteCreate, NoteRead, NoteUpdate

router = APIRouter(prefix="/notes", tags=["notes"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> NoteService:
    return NoteService(session)


@router.get("", response_model=Page[NoteRead])
async def list_notes(
    _current_user: CurrentUser,
    service: Annotated[NoteService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    target_id: Annotated[UUID | None, Query(description="Filter by target")] = None,
    scan_id: Annotated[UUID | None, Query(description="Filter by scan")] = None,
    dimension: Annotated[str | None, Query(description="Result dimension")] = None,
    asset_key: Annotated[str | None, Query(description="Asset identity")] = None,
    tag: Annotated[list[UUID] | None, Query(description="Filter by tag")] = None,
    status_filter: Annotated[
        list[str] | None, Query(alias="status", description="open or resolved")
    ] = None,
    search: Annotated[str | None, Query(description="Free text")] = None,
):
    query = await service.list(
        project_id,
        target_id=target_id,
        scan_id=scan_id,
        dimension=dimension,
        asset_key=asset_key,
        tag_ids=tag,
        statuses=status_filter,
        search=search,
    )
    return await paginate(
        service.session,
        query,
        unique=False,
        transformer=lambda rows: [service.to_read(*row) for row in rows],
    )


@router.get("/counts", response_model=list[NoteCount])
async def note_counts(
    _current_user: CurrentUser,
    service: Annotated[NoteService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    dimension: Annotated[str | None, Query(description="Result dimension")] = None,
    target_id: Annotated[UUID | None, Query(description="Filter by target")] = None,
    scan_id: Annotated[UUID | None, Query(description="Filter by scan")] = None,
):
    return await service.counts(
        project_id, dimension=dimension, target_id=target_id, scan_id=scan_id
    )


@router.post("", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
async def create_note(
    data: NoteCreate,
    current_user: CurrentUser,
    service: Annotated[NoteService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.create(
        data=data, project_id=project_id, created_by=current_user.id
    )


@router.patch("/{note_id}", response_model=NoteRead)
async def update_note(
    note_id: UUID,
    data: NoteUpdate,
    _current_user: CurrentUser,
    service: Annotated[NoteService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.update(note_id=note_id, data=data, project_id=project_id)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[NoteService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    await service.delete(note_id=note_id, project_id=project_id)
