from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from app.services.surface_scope import SurfaceScopeService
from shared.definitions.surface import SURFACE_ORDER, SurfaceDimension
from shared.models.surface import SurfaceCoverage, SurfaceOverview

router = APIRouter(prefix="/surface", tags=["surface"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SurfaceScopeService:
    return SurfaceScopeService(session)


@router.get("/overview", response_model=SurfaceOverview)
async def surface_overview(
    _current_user: CurrentUser,
    service: Annotated[SurfaceScopeService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.overview(project_id)


@router.get("/coverage", response_model=SurfaceCoverage)
async def surface_coverage(
    _current_user: CurrentUser,
    service: Annotated[SurfaceScopeService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    dimension: Annotated[SurfaceDimension, Query(description="Result dimension")],
):
    if dimension.value not in SURFACE_ORDER:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown dimension '{dimension}'.",
        )
    return await service.coverage(project_id, dimension.value)
