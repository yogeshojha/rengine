from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from app.services.http_asset import HttpAssetService
from shared.models.http_asset import HttpAssetDetail

router = APIRouter(
    prefix="/http-assets",
    tags=["http-assets"],
)


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> HttpAssetService:
    return HttpAssetService(session)


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
