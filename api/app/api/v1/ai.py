from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentSuperuser, CurrentUser
from app.core.database import get_session
from app.services.ai_settings import AiSettingsService
from shared.models.ai import (
    AiSettingsUpdate,
    AiStatus,
    AiTestRequest,
    AiTestResult,
    AiUsageRead,
)

router = APIRouter(prefix="/ai", tags=["ai"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("/status", response_model=AiStatus)
async def ai_status(_current_user: CurrentUser, session: Session):
    return await AiSettingsService(session).status()


@router.get("/catalog", response_model=dict)
async def ai_catalog(_current_user: CurrentUser):
    return AiSettingsService.catalog()


@router.get("/usage", response_model=AiUsageRead)
async def ai_usage(_current_user: CurrentUser, session: Session):
    return await AiSettingsService(session).usage()


@router.patch("/settings", response_model=AiStatus)
async def update_ai(_admin: CurrentSuperuser, session: Session, body: AiSettingsUpdate):
    return await AiSettingsService(session).update(body)


@router.post("/test", response_model=AiTestResult)
async def test_ai(_admin: CurrentSuperuser, session: Session, body: AiTestRequest):
    return await AiSettingsService(session).test(body)


@router.delete("/cache", response_model=dict)
async def clear_ai_cache(_admin: CurrentSuperuser, session: Session):
    removed = await AiSettingsService(session).clear_cache()
    return {"removed": removed}
