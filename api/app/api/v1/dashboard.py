from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from app.services.dashboard import DashboardService
from app.services.dashboard_overview import DashboardOverviewService
from shared.definitions.dashboard import DEFAULT_WINDOW
from shared.models.dashboard import (
    DashboardDiscovery,
    DashboardOverview,
    DashboardSignals,
)

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
)


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DashboardService:
    return DashboardService(session)


@router.get("/signals", response_model=DashboardSignals)
async def dashboard_signals(
    _current_user: CurrentUser,
    service: Annotated[DashboardService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.signals(project_id=project_id)


def get_overview_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DashboardOverviewService:
    return DashboardOverviewService(session)


@router.get("/overview", response_model=DashboardOverview)
async def dashboard_overview(
    _current_user: CurrentUser,
    service: Annotated[DashboardOverviewService, Depends(get_overview_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    window: Annotated[str, Query(description="Change window")] = DEFAULT_WINDOW,
):
    return await service.overview(project_id=project_id, window=window)


@router.get("/discovery", response_model=DashboardDiscovery)
async def dashboard_discovery(
    _current_user: CurrentUser,
    service: Annotated[DashboardOverviewService, Depends(get_overview_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.discovery(project_id=project_id)
