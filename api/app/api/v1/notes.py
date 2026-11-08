from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi_pagination.ext.sqlalchemy import paginate
from pydantic import StringConstraints
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.api.pagination import Page
from app.core.database import get_session
from app.services.note import NoteService
from shared.definitions.notes import (
    MAX_ASSET_KEY,
    MAX_NOTE_FACET_VALUES,
    MAX_NOTE_TAG_CHARS,
    MAX_NOTE_TAGS,
    NOTE_ASSET_SEPARATOR,
    NOTE_STATUSES,
    NOTE_SUBJECTS,
    TRIAGE_REASON_STATES,
)
from shared.definitions.surface import SurfaceDimension
from shared.models.note import (
    NoteCreate,
    NoteFacets,
    NoteFilter,
    NoteRead,
    NoteTagCount,
    NoteUpdate,
)

router = APIRouter(prefix="/notes", tags=["notes"])

_DIMENSIONS = (*(d.value for d in SurfaceDimension), *NOTE_SUBJECTS)
_DIMENSION_CHARS = max(map(len, _DIMENSIONS))
_Dimension = Annotated[str, StringConstraints(max_length=_DIMENSION_CHARS)]
_Asset = Annotated[
    str,
    StringConstraints(
        max_length=_DIMENSION_CHARS + len(NOTE_ASSET_SEPARATOR) + MAX_ASSET_KEY
    ),
]
_Tag = Annotated[str, StringConstraints(max_length=MAX_NOTE_TAG_CHARS + 1)]
_Status = Annotated[str, StringConstraints(max_length=max(map(len, NOTE_STATUSES)))]
_Triage = Annotated[
    str, StringConstraints(max_length=max(map(len, TRIAGE_REASON_STATES)))
]


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> NoteService:
    return NoteService(session)


def note_filter(
    target_id: Annotated[
        list[UUID] | None,
        Query(
            description="Notes on any of these targets",
            max_length=MAX_NOTE_FACET_VALUES,
        ),
    ] = None,
    scan_id: Annotated[
        UUID | None,
        Query(description="Notes written in this scan or on an asset it observed"),
    ] = None,
    scan: Annotated[
        list[UUID] | None,
        Query(
            description="Notes written in any of these scans",
            max_length=MAX_NOTE_FACET_VALUES,
        ),
    ] = None,
    dimension: Annotated[
        list[_Dimension] | None,
        Query(
            description="Result dimension, target or scan",
            max_length=len(_DIMENSIONS),
        ),
    ] = None,
    asset_key: Annotated[
        str | None, Query(description="Asset identity", max_length=MAX_ASSET_KEY)
    ] = None,
    asset: Annotated[
        list[_Asset] | None,
        Query(
            description="Dimension and asset identity as dimension:key",
            max_length=MAX_NOTE_FACET_VALUES,
        ),
    ] = None,
    tag: Annotated[
        list[_Tag] | None,
        Query(description="Notes carrying every tag named", max_length=MAX_NOTE_TAGS),
    ] = None,
    status_filter: Annotated[
        list[_Status] | None,
        Query(
            alias="status",
            description="open or resolved",
            max_length=len(NOTE_STATUSES),
        ),
    ] = None,
    author: Annotated[
        list[UUID] | None,
        Query(
            description="Notes written by any of these users",
            max_length=MAX_NOTE_FACET_VALUES,
        ),
    ] = None,
    triage: Annotated[
        list[_Triage] | None,
        Query(
            description="Review state of a triage reason",
            max_length=len(TRIAGE_REASON_STATES),
        ),
    ] = None,
    search: Annotated[
        str | None, Query(description="Text in the body or title", max_length=200)
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
        str | None,
        Query(description="Text in an asset label or key", max_length=MAX_ASSET_KEY),
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
    current_user: CurrentUser,
    service: Annotated[NoteService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.update(
        note_id=note_id, data=data, project_id=project_id, actor=current_user
    )


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: UUID,
    current_user: CurrentUser,
    service: Annotated[NoteService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    await service.delete(note_id=note_id, project_id=project_id, actor=current_user)
