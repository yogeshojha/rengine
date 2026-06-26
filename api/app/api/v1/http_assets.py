from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from app.services.http_asset import HttpAssetService
from shared.models.http_asset import HttpAssetDetail, HttpAssetRead, HttpAssetSummary

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


@router.get("/{asset_id}", response_model=HttpAssetDetail)
async def get_http_asset(
    _current_user: CurrentUser,
    service: Annotated[HttpAssetService, Depends(get_service)],
    asset_id: UUID,
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    detail = await service.get(asset_id, project_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="HTTP asset not found"
        )
    return detail
