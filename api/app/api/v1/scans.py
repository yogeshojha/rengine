from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from app.services.scan import ScanService, ScanSortDir, ScanSortKey
from shared.enums.scan import ScanStatus
from shared.models.scan import (
    ScanChanges,
    ScanCreate,
    ScanExportRow,
    ScanRead,
    ScanStats,
    ScanTargetGroup,
)
from shared.models.scan_activity import ScanActivityRead
from shared.models.scan_command import ScanCommandDetail, ScanCommandRead
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


@router.get("", response_model=Page[ScanRead])
async def list_scans(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[ScanService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    target_id: Annotated[UUID | None, Query(description="Filter by target ID")] = None,
    status: Annotated[
        list[ScanStatus] | None, Query(description="Filter by status")
    ] = None,
    engine: Annotated[
        list[str] | None, Query(description="Filter by engine name")
    ] = None,
    context: Annotated[
        list[str] | None, Query(description="Filter by context name")
    ] = None,
    search: Annotated[
        str | None, Query(description="Search target, engine, or context")
    ] = None,
    time_range: Annotated[
        str | None, Query(description="Time window: 24h, 7d, 30d")
    ] = None,
    sort_by: Annotated[ScanSortKey, Query(description="Sort field")] = "started",
    sort_dir: Annotated[ScanSortDir, Query(description="Sort direction")] = "desc",
):
    query = service.build_list_query(
        project_id=project_id,
        target_id=target_id,
        statuses=[s.value for s in status] if status else None,
        engines=engine,
        contexts=context,
        search=search,
        time_range=time_range,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    page = await paginate(
        session,
        query,
        transformer=lambda items: [service.to_read(s) for s in items],
    )
    if page.items:
        scan_ids = [i.id for i in page.items]
        target_ids = list({i.target_id for i in page.items})
        new_counts = await service.new_subdomain_counts(scan_ids, target_ids)
        gone_counts = await service.gone_subdomain_counts(scan_ids, target_ids)
        prev_counts = await service.prev_completed_counts(scan_ids, target_ids)
        first_ids = await service.first_scan_ids(target_ids)
        for i in page.items:
            i.new_subdomains = new_counts.get(i.id, 0)
            i.gone_subdomains = gone_counts.get(i.id, 0)
            i.prev_subdomains_found = prev_counts.get(i.id)
            i.is_first_scan = i.id in first_ids
    return page


@router.get("/stats", response_model=ScanStats)
async def scan_stats(
    _current_user: CurrentUser,
    service: Annotated[ScanService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    target_id: Annotated[UUID | None, Query(description="Filter by target ID")] = None,
):
    return await service.stats(project_id=project_id, target_id=target_id)


@router.get("/targets", response_model=Page[ScanTargetGroup])
async def list_scan_target_groups(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[ScanService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    status: Annotated[list[ScanStatus] | None, Query()] = None,
    engine: Annotated[list[str] | None, Query()] = None,
    context: Annotated[list[str] | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
    time_range: Annotated[str | None, Query()] = None,
):
    query = service.build_target_groups_query(
        project_id=project_id,
        statuses=[s.value for s in status] if status else None,
        engines=engine,
        contexts=context,
        search=search,
        time_range=time_range,
    )
    page = await paginate(
        session,
        query,
        transformer=lambda rows: [
            ScanTargetGroup(
                target_id=r.target_id,
                target_value=r.target_value,
                target_type=getattr(r.target_type, "value", r.target_type),
                scan_count=r.scan_count,
                last_scan_at=r.last_scan_at,
                last_status=r.last_status,
                running=r.running or 0,
            )
            for r in rows
        ],
    )
    if page.items:
        trends = await service.target_trends([g.target_id for g in page.items])
        for g in page.items:
            g.trend = trends.get(g.target_id, [])
    return page


@router.get("/changes", response_model=ScanChanges)
async def scan_changes(
    _current_user: CurrentUser,
    service: Annotated[ScanService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    window: Annotated[str, Query(description="Window: 24h, 7d, 30d")] = "7d",
    target_id: Annotated[UUID | None, Query(description="Filter by target ID")] = None,
):
    return await service.changes(
        project_id=project_id, window=window, target_id=target_id
    )


@router.get("/export", response_model=list[ScanExportRow])
async def export_scans(
    _current_user: CurrentUser,
    service: Annotated[ScanService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    target_id: Annotated[UUID | None, Query(description="Filter by target ID")] = None,
    status: Annotated[list[ScanStatus] | None, Query()] = None,
    engine: Annotated[list[str] | None, Query()] = None,
    context: Annotated[list[str] | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
    time_range: Annotated[str | None, Query()] = None,
    sort_by: Annotated[ScanSortKey, Query()] = "started",
    sort_dir: Annotated[ScanSortDir, Query()] = "desc",
):
    return await service.export_rows(
        project_id=project_id,
        target_id=target_id,
        statuses=[s.value for s in status] if status else None,
        engines=engine,
        contexts=context,
        search=search,
        time_range=time_range,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


@router.get("/{id}", response_model=ScanRead)
async def get_scan(
    id: UUID,
    _current_user: CurrentUser,
    service: Annotated[ScanService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.get(id=id, project_id=project_id)


@router.get("/{id}/activities", response_model=list[ScanActivityRead])
async def list_scan_activities(
    id: UUID,
    _current_user: CurrentUser,
    service: Annotated[ScanService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.list_activities(scan_id=id, project_id=project_id)


@router.get("/{id}/commands", response_model=list[ScanCommandRead])
async def list_scan_commands(
    id: UUID,
    _current_user: CurrentUser,
    service: Annotated[ScanService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    activity_id: Annotated[
        UUID | None, Query(description="Filter by stage activity ID")
    ] = None,
):
    return await service.list_commands(
        scan_id=id, project_id=project_id, activity_id=activity_id
    )


@router.get("/{id}/commands/{command_id}", response_model=ScanCommandDetail)
async def get_scan_command(
    id: UUID,
    command_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[ScanService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.get_command(
        scan_id=id, command_id=command_id, project_id=project_id
    )


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
