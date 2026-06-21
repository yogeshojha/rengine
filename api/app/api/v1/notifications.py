from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentSuperuser, CurrentUser
from app.config import settings
from app.core.database import get_session
from app.debug.notifications import DEBUG_NOTIFICATION_TEMPLATES
from shared.models.notification import (
    Notification,
    NotificationCreate,
    NotificationRead,
    NotificationStats,
)
from shared.services.notification import NotificationManager

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
)


@router.get("/stats", response_model=NotificationStats)
async def get_notification_stats(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    total_result = await session.execute(select(func.count(Notification.id)))
    total = total_result.scalar_one()

    unread_result = await session.execute(
        select(func.count(Notification.id)).where(Notification.is_read.is_(False))
    )

    unread = unread_result.scalar_one()

    return NotificationStats(total=total, unread=unread)


@router.get("", response_model=Page[NotificationRead])
async def list_notifications(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    query = select(Notification).order_by(Notification.created_at.desc())
    return await paginate(session, query)


@router.get("/unread", response_model=Page[NotificationRead])
async def list_unread_notifications(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    query = (
        select(Notification)
        .where(Notification.is_read.is_(False))
        .order_by(Notification.created_at.desc())
    )
    return await paginate(session, query)


@router.post("", response_model=NotificationRead, status_code=status.HTTP_201_CREATED)
async def create_notification(
    notification_in: NotificationCreate,
    _current_user: CurrentSuperuser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    notification = await NotificationManager.publish(
        session=session,
        type=notification_in.type,
        severity=notification_in.severity,
        title=notification_in.title,
        message=notification_in.message,
        metadata=notification_in.notification_metadata,
    )

    return NotificationRead(**notification.model_dump())


@router.patch("/{notification_id}/read", response_model=dict)
async def mark_notification_as_read(
    notification_id: int,
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    updated = await NotificationManager.mark_as_read(
        session=session,
        notification_id=notification_id,
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    return {"success": True, "message": "Notification marked as read"}


@router.post("/read-all", response_model=dict)
async def mark_all_notifications_as_read(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    count = await NotificationManager.mark_all_as_read(session=session)

    return {
        "success": True,
        "message": f"Marked {count} notifications as read",
        "count": count,
    }


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: int,
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    deleted = await NotificationManager.delete_notification(
        session=session,
        notification_id=notification_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def clear_all_notifications(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    await NotificationManager.clear_all(session=session)


if settings.DEBUG:
    import random

    @router.post("/debug/publish-random", response_model=NotificationRead)
    async def debug_publish_random_notification(
        _current_user: CurrentUser,
        session: Annotated[AsyncSession, Depends(get_session)],
    ):
        template = random.choice(DEBUG_NOTIFICATION_TEMPLATES)  # noqa: S311

        notification = await NotificationManager.publish(
            session=session,
            type=template["type"],
            severity=template["severity"],
            title=template["title"],
            message=template["message"],
            metadata=template["metadata"],
        )

        return NotificationRead(**notification.model_dump())
