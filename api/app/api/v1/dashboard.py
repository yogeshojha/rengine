from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.api.scope import TargetFilterDep
from app.core.database import get_session
from app.services.dashboard import DashboardService
from app.services.dashboard_activity import DashboardActivityService
from app.services.dashboard_overview import DashboardOverviewService
from app.services.dashboard_surface_risk import SurfaceRiskService
from app.services.instance_settings import InstanceSettingsService
from app.services.readiness import ReadinessService
from app.services.target_scope import resolve_targets
from shared.definitions.dashboard import DEFAULT_WINDOW
from shared.definitions.mode_features import CAP_BOUNTY_PROGRAMS, has_capability
from shared.models.dashboard import (
    DashboardActivity,
    DashboardDiscovery,
    DashboardOverview,
    DashboardPrograms,
    DashboardReadiness,
    DashboardSignals,
    DashboardSurfaceRisk,
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
    spec: TargetFilterDep,
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    targets = await resolve_targets(service.session, project_id, spec)
    return await service.signals(project_id=project_id, targets=targets)


def get_overview_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DashboardOverviewService:
    return DashboardOverviewService(session)


@router.get("/overview", response_model=DashboardOverview)
async def dashboard_overview(
    _current_user: CurrentUser,
    service: Annotated[DashboardOverviewService, Depends(get_overview_service)],
    spec: TargetFilterDep,
    project_id: Annotated[UUID, Query(description="Project ID")],
    window: Annotated[str, Query(description="Change window")] = DEFAULT_WINDOW,
):
    targets = await resolve_targets(service.session, project_id, spec)
    return await service.overview(project_id=project_id, window=window, targets=targets)


@router.get("/surface-risk", response_model=DashboardSurfaceRisk)
async def dashboard_surface_risk(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    spec: TargetFilterDep,
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    targets = await resolve_targets(session, project_id, spec)
    return await SurfaceRiskService(session).rows(project_id, targets)


@router.get("/discovery", response_model=DashboardDiscovery)
async def dashboard_discovery(
    _current_user: CurrentUser,
    service: Annotated[DashboardOverviewService, Depends(get_overview_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.discovery(project_id=project_id)


@router.get("/readiness", response_model=DashboardReadiness)
async def dashboard_readiness(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    return await ReadinessService(session).readiness()


async def _programs_enabled(session: AsyncSession) -> bool:
    settings = await InstanceSettingsService(session).get_or_create()
    return has_capability(settings.mode, CAP_BOUNTY_PROGRAMS)


@router.get("/activity", response_model=DashboardActivity)
async def dashboard_activity(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    spec: TargetFilterDep,
    project_id: Annotated[UUID, Query(description="Project ID")],
    window: Annotated[str, Query(description="Change window")] = DEFAULT_WINDOW,
):
    programs = await _programs_enabled(session)
    targets = await resolve_targets(session, project_id, spec)
    return await DashboardActivityService(session).activity(
        project_id, window, programs=programs, targets=targets
    )


@router.get("/programs", response_model=DashboardPrograms)
async def dashboard_programs(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    window: Annotated[str, Query(description="Change window")] = DEFAULT_WINDOW,
):
    if not await _programs_enabled(session):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bug bounty programs require bug bounty mode.",
        )
    return await DashboardActivityService(session).programs(project_id, window)
