from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.capability import require_capability
from app.api.deps import CurrentUser
from app.api.scope import TargetFilterDep
from app.core.database import get_session
from app.services.dashboard_activity import DashboardActivityService
from app.services.dashboard_overview import DashboardOverviewService
from app.services.dashboard_surface_risk import SurfaceRiskService
from app.services.dashboard_window import DashboardWindowService
from app.services.instance_settings import InstanceSettingsService
from app.services.readiness import ReadinessService
from app.services.target_scope import resolve_targets
from shared.definitions.dashboard import DEFAULT_WINDOW
from shared.definitions.mode_features import CAP_BOUNTY_PROGRAMS
from shared.models.dashboard import (
    DashboardActivity,
    DashboardDiscovery,
    DashboardOverview,
    DashboardPrograms,
    DashboardReadiness,
    DashboardSurfaceRisk,
    DashboardWindowCounts,
)

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
)


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


@router.get("/window", response_model=DashboardWindowCounts)
async def dashboard_window(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    spec: TargetFilterDep,
    project_id: Annotated[UUID, Query(description="Project ID")],
    window: Annotated[str, Query(description="Change window")] = DEFAULT_WINDOW,
):
    targets = await resolve_targets(session, project_id, spec)
    return await DashboardWindowService(session).counts(project_id, window, targets)


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


@router.get("/activity", response_model=DashboardActivity)
async def dashboard_activity(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    spec: TargetFilterDep,
    project_id: Annotated[UUID, Query(description="Project ID")],
    window: Annotated[str, Query(description="Change window")] = DEFAULT_WINDOW,
):
    programs = await InstanceSettingsService(session).has_capability(
        CAP_BOUNTY_PROGRAMS
    )
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
    await require_capability(session, CAP_BOUNTY_PROGRAMS)
    return await DashboardActivityService(session).programs(project_id, window)
