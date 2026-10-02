from datetime import date, datetime
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from app.services.instance_settings import InstanceSettingsService
from app.services.whats_new import WhatsNewService
from shared.definitions.mode_features import CAP_BOUNTY_PROGRAMS
from shared.definitions.whats_new import (
    DEFAULT_ZONE,
    KIND_ORDER,
    MAX_TEXT_FILTER,
    NEW_WINDOWS,
    ProgramRing,
)
from shared.models.whats_new import NewFeed, NewMark, NewUnseen, VisualFeed

router = APIRouter(prefix="/whats-new", tags=["whats-new"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> WhatsNewService:
    return WhatsNewService(session)


ServiceDep = Annotated[WhatsNewService, Depends(get_service)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _zone(tz: str) -> None:
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unknown time zone {tz}.",
        ) from exc


def _check_range(window: str | None, day: date | None, day_to: date | None) -> None:
    if window is not None and window not in NEW_WINDOWS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Window must be one of {', '.join(NEW_WINDOWS)}.",
        )
    if day_to is not None and (day is None or day_to < day):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="day_to needs a day at or before it.",
        )


@router.get("", response_model=NewFeed)
async def whats_new(
    current_user: CurrentUser,
    service: ServiceDep,
    session: SessionDep,
    project_id: Annotated[UUID, Query(description="Project ID")],
    since: datetime | None = None,
    window: Annotated[str | None, Query(max_length=8)] = None,
    day: date | None = None,
    day_to: date | None = None,
    target_id: UUID | None = None,
    platform: Annotated[str | None, Query(max_length=32)] = None,
    handle: Annotated[str | None, Query(max_length=200)] = None,
    kinds: Annotated[str | None, Query(max_length=160)] = None,
    ring: ProgramRing = ProgramRing.ENGAGED,
    q: Annotated[str | None, Query(max_length=MAX_TEXT_FILTER)] = None,
    tz: Annotated[str, Query(max_length=64)] = DEFAULT_ZONE,
) -> NewFeed:
    _zone(tz)
    _check_range(window, day, day_to)
    wanted = {k.strip() for k in kinds.split(",") if k.strip()} if kinds else None
    if wanted and not wanted <= set(KIND_ORDER):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Kinds must be among {', '.join(KIND_ORDER)}.",
        )
    return await service.feed(
        project_id,
        current_user.id,
        since=since,
        window=window,
        day_from=day,
        day_to=day_to,
        target_id=target_id,
        platform=platform,
        handle=handle,
        kinds=wanted,
        ring=ring,
        q=q,
        tz=tz,
        bounty=await InstanceSettingsService(session).has_capability(
            CAP_BOUNTY_PROGRAMS
        ),
    )


@router.get("/visual", response_model=VisualFeed)
async def whats_new_visual(
    current_user: CurrentUser,
    service: ServiceDep,
    project_id: Annotated[UUID, Query(description="Project ID")],
    since: datetime | None = None,
    window: Annotated[str | None, Query(max_length=8)] = None,
    day: date | None = None,
    day_to: date | None = None,
    target_id: UUID | None = None,
    q: Annotated[str | None, Query(max_length=MAX_TEXT_FILTER)] = None,
    tz: Annotated[str, Query(max_length=64)] = DEFAULT_ZONE,
) -> VisualFeed:
    _zone(tz)
    _check_range(window, day, day_to)
    return await service.visual(
        project_id,
        current_user.id,
        since=since,
        window=window,
        day_from=day,
        day_to=day_to,
        target_id=target_id,
        q=q,
        tz=tz,
    )


@router.get("/unseen", response_model=NewUnseen)
async def whats_new_unseen(
    current_user: CurrentUser,
    service: ServiceDep,
    session: SessionDep,
    project_id: Annotated[UUID, Query(description="Project ID")],
    tz: Annotated[str, Query(max_length=64)] = DEFAULT_ZONE,
) -> NewUnseen:
    _zone(tz)
    bounty = await InstanceSettingsService(session).has_capability(CAP_BOUNTY_PROGRAMS)
    count = await service.unseen(project_id, current_user.id, bounty=bounty, tz=tz)
    return NewUnseen(count=count, since=await service.mark(current_user.id, project_id))


@router.post("/seen", response_model=NewMark)
async def whats_new_seen(
    current_user: CurrentUser,
    service: ServiceDep,
    project_id: Annotated[UUID, Query(description="Project ID")],
) -> NewMark:
    return NewMark(marked_at=await service.mark_seen(current_user.id, project_id))
