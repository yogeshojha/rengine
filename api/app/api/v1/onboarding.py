from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentSuperuser, CurrentUser
from app.api.v1.projects import generate_unique_slug
from app.core.database import get_session
from app.services.instance_settings import InstanceSettingsService
from shared.models.api_key import APIKey
from shared.models.notification_channel import NotificationChannel
from shared.models.project import Project, ProjectCreate, ProjectRead
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
    ai_enabled: bool


class OnboardingStatus(BaseModel):
    completed: bool
    can_setup: bool
    current_step: int
    instance_name: str
    mode: str
    summary: OnboardingSummary


async def _summary(session: AsyncSession, ai_enabled: bool) -> OnboardingSummary:
    proxies = await session.execute(select(func.count(Proxy.id)).where(Proxy.is_active))
    channels = await session.execute(
        select(func.count(NotificationChannel.id)).where(NotificationChannel.is_active)
    )
    integrations = await session.execute(
        select(func.count(APIKey.id)).where(APIKey.is_enabled)
    )
    return OnboardingSummary(
        proxies=proxies.scalar_one(),
        channels=channels.scalar_one(),
        integrations=integrations.scalar_one(),
        ai_enabled=ai_enabled,
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
        summary=await _summary(session, settings.ai_enabled),
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


@router.post("/first-project", response_model=ProjectRead)
async def create_first_project(
    data: ProjectCreate,
    current_user: CurrentSuperuser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    slug = await generate_unique_slug(data.name, session)
    project = Project(
        name=data.name,
        slug=slug,
        description=data.description,
        label=data.label,
        created_by=current_user.id,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project
