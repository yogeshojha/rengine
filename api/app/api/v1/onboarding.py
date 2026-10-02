from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentSuperuser, CurrentUser
from app.core.database import get_session
from app.services.instance_settings import InstanceSettingsService
from shared.definitions.api_keys import API_PROVIDER_META, RECON_GROUPS
from shared.definitions.oast import OastMode, off_reason
from shared.enums.api_key import ProviderGroup
from shared.models.api_key import APIKey
from shared.models.instance_settings import InstanceSettings
from shared.models.notification_channel import NotificationChannel
from shared.models.proxy import Proxy
from shared.utils.datetime import utc_now

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> InstanceSettingsService:
    return InstanceSettingsService(session)


class OnboardingProgress(BaseModel):
    current_step: int
    state: dict


class OnboardingSummary(BaseModel):
    proxies: int
    channels: int
    integrations: int
    platforms: int
    ai_enabled: bool
    oast_mode: str


class OnboardingStatus(BaseModel):
    completed: bool
    can_setup: bool
    current_step: int
    instance_name: str
    mode: str
    summary: OnboardingSummary


async def _summary(
    session: AsyncSession, settings: InstanceSettings
) -> OnboardingSummary:
    proxies = await session.execute(select(func.count(Proxy.id)).where(Proxy.is_active))
    channels = await session.execute(
        select(func.count(NotificationChannel.id)).where(NotificationChannel.is_active)
    )
    enabled = (
        await session.execute(select(APIKey.provider).where(APIKey.is_enabled))
    ).scalars()
    groups = [API_PROVIDER_META[p]["group"] for p in enabled if p in API_PROVIDER_META]
    oast_off = off_reason(
        settings.oast_mode,
        server=settings.oast_server,
        acknowledged=settings.oast_public_acknowledged,
    )
    return OnboardingSummary(
        proxies=proxies.scalar_one(),
        channels=channels.scalar_one(),
        integrations=sum(group in RECON_GROUPS for group in groups),
        platforms=groups.count(ProviderGroup.BOUNTY_PLATFORMS.value),
        ai_enabled=settings.ai_enabled,
        oast_mode=OastMode.OFF.value if oast_off else settings.oast_mode,
    )


async def _status(
    session: AsyncSession, service: InstanceSettingsService, can_setup: bool
) -> OnboardingStatus:
    settings = await service.get_or_create()
    return OnboardingStatus(
        completed=settings.onboarding_completed,
        can_setup=can_setup,
        current_step=settings.onboarding_step,
        instance_name=settings.instance_name,
        mode=settings.mode,
        summary=await _summary(session, settings),
    )


@router.get("/status", response_model=OnboardingStatus)
async def get_status(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[InstanceSettingsService, Depends(get_service)],
):
    return await _status(session, service, can_setup=current_user.is_superuser)


@router.patch("/progress", response_model=OnboardingStatus)
async def update_progress(
    data: OnboardingProgress,
    _current_user: CurrentSuperuser,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[InstanceSettingsService, Depends(get_service)],
):
    settings = await service.get_or_create()
    settings.onboarding_step = data.current_step
    settings.onboarding_state = dict(data.state)
    settings.updated_at = utc_now()
    await session.commit()
    return await _status(session, service, can_setup=True)


@router.post("/complete", response_model=OnboardingStatus)
async def complete_onboarding(
    current_user: CurrentSuperuser,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[InstanceSettingsService, Depends(get_service)],
):
    settings = await service.get_or_create()
    if not settings.onboarding_completed:
        settings.onboarding_completed = True
        settings.onboarding_completed_at = utc_now()
        settings.onboarding_completed_by = current_user.id
        settings.updated_at = utc_now()
        await session.commit()
    return await _status(session, service, can_setup=True)
