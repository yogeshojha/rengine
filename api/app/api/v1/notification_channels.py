from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentSuperuser
from app.core.database import get_session
from app.services.notification_channel import NotificationChannelService
from shared.models.notification_channel import (
    NotificationChannelCreate,
    NotificationChannelRead,
    NotificationChannelTestConfig,
    NotificationChannelTestResult,
    NotificationChannelUpdate,
)

router = APIRouter(
    prefix="/notification-channels",
    tags=["notification-channels"],
)


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> NotificationChannelService:
    return NotificationChannelService(session)


@router.get("", response_model=list[NotificationChannelRead])
async def list_channels(
    _current_user: CurrentSuperuser,
    service: Annotated[NotificationChannelService, Depends(get_service)],
):
    return await service.list()


@router.post(
    "", response_model=NotificationChannelRead, status_code=status.HTTP_201_CREATED
)
async def create_channel(
    data: NotificationChannelCreate,
    current_user: CurrentSuperuser,
    service: Annotated[NotificationChannelService, Depends(get_service)],
):
    return await service.create(data, created_by=current_user.id)


@router.post("/test", response_model=NotificationChannelTestResult)
async def test_channel_config(
    data: NotificationChannelTestConfig,
    _current_user: CurrentSuperuser,
    service: Annotated[NotificationChannelService, Depends(get_service)],
):
    return await service.test_config(data.provider, data.config)


@router.get("/{id}", response_model=NotificationChannelRead)
async def get_channel(
    id: UUID,
    _current_user: CurrentSuperuser,
    service: Annotated[NotificationChannelService, Depends(get_service)],
):
    return await service.get(id)


@router.patch("/{id}", response_model=NotificationChannelRead)
async def update_channel(
    id: UUID,
    data: NotificationChannelUpdate,
    _current_user: CurrentSuperuser,
    service: Annotated[NotificationChannelService, Depends(get_service)],
):
    return await service.update(id, data)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(
    id: UUID,
    _current_user: CurrentSuperuser,
    service: Annotated[NotificationChannelService, Depends(get_service)],
):
    await service.delete(id)


@router.post("/{id}/test", response_model=NotificationChannelTestResult)
async def test_channel(
    id: UUID,
    _current_user: CurrentSuperuser,
    service: Annotated[NotificationChannelService, Depends(get_service)],
):
    return await service.test(id)
