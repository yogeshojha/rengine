from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from app.services.http_asset import HttpAssetService
from shared.models.http_asset import HttpAssetRead, HttpAssetSummary

router = APIRouter(
    prefix="/http-assets",
    tags=["http-assets"],
)


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> HttpAssetService:
    return HttpAssetService(session)


@router.get("", response_model=list[HttpAssetRead])
async def list_http_assets(
    _current_user: CurrentUser,
    service: Annotated[HttpAssetService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    scan_id: Annotated[UUID | None, Query(description="Filter by scan ID")] = None,
    target_id: Annotated[UUID | None, Query(description="Filter by target ID")] = None,
    search: Annotated[str | None, Query(description="Substring match on URL")] = None,
    limit: Annotated[int, Query(ge=1, le=1000, description="Max rows")] = 100,
    offset: Annotated[int, Query(ge=0, description="Rows to skip")] = 0,
):
    return await service.list(
        project_id=project_id,
        scan_id=scan_id,
        target_id=target_id,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get("/summary", response_model=HttpAssetSummary)
async def http_asset_summary(
    _current_user: CurrentUser,
    service: Annotated[HttpAssetService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    scan_id: Annotated[UUID | None, Query(description="Filter by scan ID")] = None,
    target_id: Annotated[UUID | None, Query(description="Filter by target ID")] = None,
):
    return await service.summary(
        project_id=project_id, scan_id=scan_id, target_id=target_id
    )
