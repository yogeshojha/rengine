from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentSuperuser, CurrentUser
from app.core.database import get_session
from app.services.ai_settings import AiSettingsService
from app.services.instance_settings import InstanceSettingsService
from shared.models.ai import AiTestRequest
from shared.models.instance_settings import (
    InstanceSettingsRead,
    InstanceSettingsUpdate,
)

router = APIRouter(prefix="/instance-settings", tags=["instance-settings"])


class AITestRequest(BaseModel):
    provider: str
    model: str | None = None
    api_key: str | None = None


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> InstanceSettingsService:
    return InstanceSettingsService(session)


@router.get("", response_model=InstanceSettingsRead)
async def get_instance_settings(
    _current_user: CurrentUser,
    service: Annotated[InstanceSettingsService, Depends(get_service)],
):
    settings = await service.get_or_create()
    return await service.with_limit(service.to_read(settings))


@router.patch("", response_model=InstanceSettingsRead)
async def update_instance_settings(
    data: InstanceSettingsUpdate,
    _current_user: CurrentSuperuser,
    service: Annotated[InstanceSettingsService, Depends(get_service)],
):
    return await service.update(data)


@router.post("/ai/test")
async def test_ai_connection(
    data: AITestRequest,
    current_user: CurrentSuperuser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await AiSettingsService(session).test(
        AiTestRequest(provider=data.provider, model=data.model, api_key=data.api_key),
        current_user.id,
    )
    return {"success": result.success, "message": result.message}
