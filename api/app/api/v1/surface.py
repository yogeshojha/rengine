from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.api.scope import resolve_scope
from app.core.database import get_session
from app.services.surface_delete import SurfaceDeleteService
from app.services.surface_scope import SurfaceScopeService
from shared.definitions.asset_query import REGISTRIES
from shared.models.asset_query import QuerySchema
from shared.models.surface import (
    SurfaceDelete,
    SurfaceDeleteResult,
    SurfaceOverview,
)
from shared.services.asset_query import build_schema

router = APIRouter(prefix="/surface", tags=["surface"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SurfaceScopeService:
    return SurfaceScopeService(session)


@router.get("/schemas", response_model=dict[str, QuerySchema])
async def surface_schemas(_current_user: CurrentUser) -> dict[str, QuerySchema]:
    return {dim: build_schema(reg) for dim, reg in REGISTRIES.items()}


@router.get("/overview", response_model=SurfaceOverview)
async def surface_overview(
    _current_user: CurrentUser,
    service: Annotated[SurfaceScopeService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.overview(project_id)


@router.post("/delete", response_model=SurfaceDeleteResult)
async def delete_rows(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    body: SurfaceDelete,
    scan_id: Annotated[UUID | None, Query(description="Scan ID")] = None,
    project_id: Annotated[UUID | None, Query(description="Project ID")] = None,
):
    scope = await resolve_scope(session, body.dimension, scan_id, project_id)
    return await SurfaceDeleteService(session).delete(
        scope, body.dimension, body.ids, body.key
    )
