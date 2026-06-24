from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from app.services.scan import ScanService
from app.services.scan_schedule import ScanScheduleService
from shared.enums.scan_schedule import ScheduleStatus
from shared.models.scan import ScanRead
from shared.models.scan_schedule import (
    ScanScheduleCreate,
    ScanScheduleRead,
    ScanScheduleUpdate,
)

router = APIRouter(prefix="/schedules", tags=["schedules"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ScanScheduleService:
    return ScanScheduleService(session)


@router.post("", response_model=ScanScheduleRead, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    data: ScanScheduleCreate,
    current_user: CurrentUser,
    service: Annotated[ScanScheduleService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.create(
        data=data, project_id=project_id, created_by=current_user.id
    )


@router.get("", response_model=list[ScanScheduleRead])
async def list_schedules(
    _current_user: CurrentUser,
    service: Annotated[ScanScheduleService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.list_schedules(project_id=project_id)


@router.get("/{id}", response_model=ScanScheduleRead)
async def get_schedule(
    id: UUID,
    _current_user: CurrentUser,
    service: Annotated[ScanScheduleService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.get(id=id, project_id=project_id)


@router.patch("/{id}", response_model=ScanScheduleRead)
async def update_schedule(
    id: UUID,
    data: ScanScheduleUpdate,
    _current_user: CurrentUser,
    service: Annotated[ScanScheduleService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.update(id=id, project_id=project_id, data=data)


@router.post("/{id}/pause", response_model=ScanScheduleRead)
async def pause_schedule(
    id: UUID,
    _current_user: CurrentUser,
    service: Annotated[ScanScheduleService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.set_status(id, project_id, ScheduleStatus.PAUSED)


@router.post("/{id}/resume", response_model=ScanScheduleRead)
async def resume_schedule(
    id: UUID,
    _current_user: CurrentUser,
    service: Annotated[ScanScheduleService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.set_status(id, project_id, ScheduleStatus.ACTIVE)


@router.post("/{id}/run-now", response_model=list[ScanRead])
async def run_schedule_now(
    id: UUID,
    current_user: CurrentUser,
    service: Annotated[ScanScheduleService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.run_now(
        id=id, project_id=project_id, created_by=current_user.id
    )


@router.get("/{id}/scans", response_model=Page[ScanRead])
async def list_schedule_scans(
    id: UUID,
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    scan_service = ScanService(session)
    query = scan_service.build_list_query(project_id=project_id, schedule_id=id)
    page = await paginate(
        session,
        query,
        transformer=lambda items: [scan_service.to_read(s) for s in items],
    )
    if page.items:
        scan_ids = [i.id for i in page.items]
        target_ids = list({i.target_id for i in page.items})
        new_counts = await scan_service.new_subdomain_counts(scan_ids, target_ids)
        for i in page.items:
            i.new_subdomains = new_counts.get(i.id, 0)
    return page


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    id: UUID,
    _current_user: CurrentUser,
    service: Annotated[ScanScheduleService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    await service.delete(id=id, project_id=project_id)
