from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.api.pagination import Page
from app.core.database import get_session
from app.services.note import NoteService
from shared.models.note import (
    NoteCreate,
    NoteFacets,
    NoteFilter,
    NoteRead,
    NoteTagCount,
    NoteUpdate,
)

router = APIRouter(prefix="/notes", tags=["notes"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> NoteService:
    return NoteService(session)


def note_filter(
    target_id: Annotated[
        list[UUID] | None, Query(description="Notes on any of these targets")
    ] = None,
    scan_id: Annotated[
        UUID | None,
        Query(description="Notes written in this scan or on an asset it observed"),
    ] = None,
    scan: Annotated[
        list[UUID] | None, Query(description="Notes written in any of these scans")
    ] = None,
    dimension: Annotated[
        list[str] | None,
        Query(description="Result dimension, target or scan"),
    ] = None,
    asset_key: Annotated[str | None, Query(description="Asset identity")] = None,
    asset: Annotated[
        list[str] | None,
        Query(description="Dimension and asset identity as dimension:key"),
    ] = None,
    tag: Annotated[
        list[str] | None, Query(description="Notes carrying every tag named")
    ] = None,
    status_filter: Annotated[
        list[str] | None, Query(alias="status", description="open or resolved")
    ] = None,
    author: Annotated[
        list[UUID] | None, Query(description="Notes written by any of these users")
    ] = None,
    triage: Annotated[
        list[str] | None, Query(description="Review state of a triage reason")
    ] = None,
    search: Annotated[
        str | None, Query(description="Text in the body or title")
    ] = None,
) -> NoteFilter:
    return NoteFilter(
        target_ids=target_id or [],
        scan_id=scan_id,
        scans=scan or [],
        dimensions=dimension or [],
        asset_key=asset_key,
        assets=asset or [],
        tags=tag or [],
        statuses=status_filter or [],
        authors=author or [],
        triage=triage or [],
        search=search,
    )


Filtered = Annotated[NoteFilter, Depends(note_filter)]


@router.get("", response_model=Page[NoteRead])
async def list_notes(
    _current_user: CurrentUser,
    service: Annotated[NoteService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    f: Filtered,
):
    query = await service.list(project_id, f)
    return await paginate(
        service.session,
        query,
        unique=False,
        transformer=lambda rows: [service.to_read(*row) for row in rows],
    )


@router.get("/facets", response_model=NoteFacets)
async def note_facets(
    _current_user: CurrentUser,
    service: Annotated[NoteService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    f: Filtered,
    asset_q: Annotated[
        str | None, Query(description="Text in an asset label or key")
    ] = None,
):
    return await service.facets(project_id, f, asset_query=asset_q)


@router.get("/tags", response_model=list[NoteTagCount])
async def list_note_tags(
    _current_user: CurrentUser,
    service: Annotated[NoteService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    q: Annotated[str | None, Query(description="Tag prefix")] = None,
):
    return await service.tags(project_id, prefix=q)


@router.get("/{note_id}", response_model=NoteRead)
async def get_note(
    note_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[NoteService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.get(note_id=note_id, project_id=project_id)


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
