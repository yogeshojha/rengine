from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_pagination.ext.sqlalchemy import apaginate
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.access import Access, OptionalProject
from app.api.deps import CurrentUser
from app.api.pagination import Page
from app.core.database import get_session
from shared.models.notification import (
    Notification,
    NotificationRead,
    NotificationReceipt,
    NotificationStats,
)
from shared.models.user import User
from shared.services.notification import NotificationManager
from shared.services.project_access import ProjectSet

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
)


def _visible(query, user: User, projects: ProjectSet):
    return NotificationManager.receipt_join(
        NotificationManager.in_scope(query, projects), user.id
    )


def _read(row) -> NotificationRead:
    notification, read_at = row
    return NotificationRead(
        **notification.model_dump(exclude={"id", "uid", "is_read"}),
        id=notification.uid,
        is_read=read_at is not None,
    )


@router.get("/stats", response_model=NotificationStats)
async def get_notification_stats(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    projects: OptionalProject,
):
    row = (
        await session.execute(
            _visible(
                select(
                    func.count(Notification.id),
                    func.count(Notification.id).filter(
                        NotificationReceipt.read_at.is_(None)
                    ),
                ),
                current_user,
                projects,
            )
        )
    ).one()
    return NotificationStats(total=row[0], unread=row[1])


@router.get("", response_model=Page[NotificationRead])
async def list_notifications(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    projects: OptionalProject,
):
    query = _visible(
        select(Notification, NotificationReceipt.read_at), current_user, projects
    ).order_by(Notification.created_at.desc())
    return await apaginate(
        session, query, unique=False, transformer=lambda rows: [_read(r) for r in rows]
    )


@router.patch("/{notification_id}/read", response_model=dict)
async def mark_notification_as_read(
    notification_id: UUID,
    current_user: CurrentUser,
    access: Access,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    updated = await NotificationManager.mark_as_read(
        session, notification_id, current_user.id, access
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )

    return {"success": True, "message": "Notification marked as read"}


@router.post("/read-all", response_model=dict)
async def mark_all_notifications_as_read(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    projects: OptionalProject,
):
    count = await NotificationManager.mark_all_as_read(
        session, current_user.id, projects
    )

    return {
        "success": True,
        "message": f"Marked {count} notifications as read",
        "count": count,
    }


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: UUID,
    current_user: CurrentUser,
    access: Access,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    deleted = await NotificationManager.dismiss(
        session, notification_id, current_user.id, access
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def clear_all_notifications(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    projects: OptionalProject,
):
    await NotificationManager.dismiss_all(session, current_user.id, projects)
