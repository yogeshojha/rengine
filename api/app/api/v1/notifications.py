from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

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

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
)

ProjectScope = Annotated[
    UUID | None,
    Query(description="Project ID. Global notifications are included."),
]


def _visible(query, user: User, project_id: UUID | None):
    return NotificationManager.receipt_join(
        NotificationManager.in_scope(query, project_id), user.id
    )


def _read(row) -> NotificationRead:
    notification, read_at = row
    return NotificationRead(
        **notification.model_dump(exclude={"is_read"}), is_read=read_at is not None
    )


@router.get("/stats", response_model=NotificationStats)
async def get_notification_stats(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    project_id: ProjectScope = None,
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
                project_id,
            )
        )
    ).one()
    return NotificationStats(total=row[0], unread=row[1])


@router.get("", response_model=Page[NotificationRead])
async def list_notifications(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    project_id: ProjectScope = None,
):
    query = _visible(
        select(Notification, NotificationReceipt.read_at), current_user, project_id
    ).order_by(Notification.created_at.desc())
    return await paginate(
        session, query, unique=False, transformer=lambda rows: [_read(r) for r in rows]
    )


@router.patch("/{notification_id}/read", response_model=dict)
async def mark_notification_as_read(
    notification_id: int,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    updated = await NotificationManager.mark_as_read(
        session, notification_id, current_user.id
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    return {"success": True, "message": "Notification marked as read"}


@router.post("/read-all", response_model=dict)
async def mark_all_notifications_as_read(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    project_id: ProjectScope = None,
):
    count = await NotificationManager.mark_all_as_read(
        session, current_user.id, project_id
    )

    return {
        "success": True,
        "message": f"Marked {count} notifications as read",
        "count": count,
    }


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: int,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    deleted = await NotificationManager.dismiss(
        session, notification_id, current_user.id
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def clear_all_notifications(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    project_id: ProjectScope = None,
):
    await NotificationManager.dismiss_all(session, current_user.id, project_id)
