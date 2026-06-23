from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from app.services.dashboard import DashboardService
from shared.models.dashboard import DashboardSignals

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
