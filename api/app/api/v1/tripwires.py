from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.api.pagination import Page
from app.core.database import get_session
from app.services.tripwire import TripwireError, TripwireService
from shared.models.tripwire import (
    TripwireBacktest,
    TripwireCatalog,
    TripwireCreate,
    TripwirePreview,
    TripwirePreviewRequest,
    TripwireRead,
    TripwireRunCounts,
    TripwireRunRead,
    TripwireUpdate,
)

router = APIRouter(prefix="/tripwires", tags=["tripwires"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
ProjectId = Annotated[UUID, Query(description="Project ID")]
NOT_FOUND = "Tripwire not found"


def get_service(session: SessionDep) -> TripwireService:
    return TripwireService(session)


ServiceDep = Annotated[TripwireService, Depends(get_service)]


@router.get("", response_model=list[TripwireRead])
async def list_tripwires(
    _user: CurrentUser, service: ServiceDep, project_id: ProjectId
) -> list[TripwireRead]:
    return await service.list(project_id)


@router.post("", response_model=TripwireRead, status_code=status.HTTP_201_CREATED)
async def create_tripwire(
    user: CurrentUser,
    service: ServiceDep,
    payload: TripwireCreate,
    project_id: ProjectId,
) -> TripwireRead:
    try:
        return await service.create(payload, project_id, user.id)
    except TripwireError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.get("/catalog", response_model=TripwireCatalog)
async def tripwire_catalog(_user: CurrentUser, service: ServiceDep) -> TripwireCatalog:
    return await service.catalog()


@router.post("/preview", response_model=TripwirePreview)
async def preview_tripwire(
    _user: CurrentUser,
    service: ServiceDep,
    payload: TripwirePreviewRequest,
    project_id: ProjectId,
) -> TripwirePreview:
    return await service.preview(payload, project_id)


@router.post("/backtest", response_model=TripwireBacktest)
async def backtest_tripwire(
    _user: CurrentUser,
    service: ServiceDep,
    payload: TripwirePreviewRequest,
    project_id: ProjectId,
) -> TripwireBacktest:
    return await service.backtest(payload, project_id)


@router.get("/runs/{run_id}", response_model=TripwireRunRead)
async def get_run(
    _user: CurrentUser,
    service: ServiceDep,
    run_id: Annotated[UUID, Path()],
    project_id: ProjectId,
) -> TripwireRunRead:
    row = await service.run(run_id, project_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Check not found")
    return row


@router.patch("/{tripwire_id}", response_model=TripwireRead)
async def update_tripwire(
    _user: CurrentUser,
    service: ServiceDep,
    tripwire_id: Annotated[UUID, Path()],
    payload: TripwireUpdate,
    project_id: ProjectId,
) -> TripwireRead:
    try:
        row = await service.update(tripwire_id, payload, project_id)
    except TripwireError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    return row


@router.delete("/{tripwire_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tripwire(
    _user: CurrentUser,
    service: ServiceDep,
    tripwire_id: Annotated[UUID, Path()],
    project_id: ProjectId,
) -> None:
    if not await service.delete(tripwire_id, project_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)


@router.get("/{tripwire_id}/runs", response_model=Page[TripwireRunRead])
async def list_runs(
    _user: CurrentUser,
    service: ServiceDep,
    session: SessionDep,
    tripwire_id: Annotated[UUID, Path()],
    project_id: ProjectId,
    status_filter: Annotated[str | None, Query(alias="status", max_length=16)] = None,
):
    if await service.get(tripwire_id, project_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    query = await service.runs(tripwire_id, project_id, status_filter)
    page = await paginate(session, query)
    return Page[TripwireRunRead](
        items=await service.run_reads(list(page.items)),
        total=page.total,
        page=page.page,
        size=page.size,
        pages=page.pages,
    )


@router.get("/{tripwire_id}/runs/counts", response_model=TripwireRunCounts)
async def run_counts(
    _user: CurrentUser,
    service: ServiceDep,
    tripwire_id: Annotated[UUID, Path()],
    project_id: ProjectId,
) -> TripwireRunCounts:
    if await service.get(tripwire_id, project_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    return await service.counts(tripwire_id, project_id)
