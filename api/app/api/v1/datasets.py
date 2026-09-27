from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentSuperuser, CurrentUser
from app.core.database import get_session
from app.services.datasets import DatasetService
from shared.models.dataset import DatasetRead, DatasetSyncResult

router = APIRouter(prefix="/datasets", tags=["Datasets"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DatasetService:
    return DatasetService(session)


@router.get("", response_model=list[DatasetRead])
async def list_datasets(
    _current_user: CurrentUser,
    service: Annotated[DatasetService, Depends(get_service)],
) -> list[DatasetRead]:
    return await service.list()


@router.post("/{kind}/sync", response_model=DatasetSyncResult)
async def sync_dataset(
    kind: str,
    _current_user: CurrentSuperuser,
    service: Annotated[DatasetService, Depends(get_service)],
) -> DatasetSyncResult:
    """Queue one dataset's download."""
    return await service.sync(kind)
