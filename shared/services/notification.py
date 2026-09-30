import uuid

from sqlalchemy import DateTime, Uuid, and_, func, literal, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from shared.enums.notification import NotificationSeverity, NotificationType
from shared.enums.sse import SSEChannel, SSEEventType
from shared.logging import get_logger
from shared.models.notification import (
    Notification,
    NotificationMetadata,
    NotificationReceipt,
)
from shared.sse import sse_manager
from shared.utils.datetime import utc_now

logger = get_logger(__name__)


class NotificationManager:
    @staticmethod
    async def publish(
        session: AsyncSession,
        type: NotificationType,
        severity: NotificationSeverity,
        title: str,
        message: str,
        metadata: NotificationMetadata | dict | None = None,
        project_id: uuid.UUID | str | None = None,
        commit: bool = True,
        channel_ids=None,
    ) -> Notification:
        if isinstance(metadata, NotificationMetadata):
            metadata_dict = metadata.model_dump(exclude_none=True)
        elif isinstance(metadata, dict):
            validated = NotificationMetadata(**metadata)
            metadata_dict = validated.model_dump(exclude_none=True)
        else:
            metadata_dict = {}

        notification = Notification(
            type=type,
            severity=severity,
            title=title[:200],
            message=message,
            notification_metadata=metadata_dict,
            project_id=uuid.UUID(str(project_id)) if project_id else None,
        )

        session.add(notification)

        if commit:
            await session.commit()
            await session.refresh(notification)
        else:
            await session.flush()

        await sse_manager.publish(
            channel=SSEChannel.BROADCAST,
            event_type=SSEEventType.NOTIFICATION,
            data={
                "id": notification.id,
                "project_id": str(notification.project_id)
                if notification.project_id
                else None,
                "type": notification.type.value,
                "severity": notification.severity.value,
                "title": notification.title,
                "message": notification.message,
                "notification_metadata": notification.notification_metadata,
                "is_read": False,
                "created_at": notification.created_at.isoformat(),
            },
        )

        logger.info(f"Published notification: {type.value}/{severity.value} - {title}")

        try:
            from shared.services.notifier import dispatch_async  # noqa: PLC0415

            await dispatch_async(
                session, type, severity, title, message, channel_ids=channel_ids
            )
        except Exception as exc:
            logger.warning(f"External notification dispatch failed: {exc}")

        return notification

    @staticmethod
    def in_scope(stmt, project_id: uuid.UUID | None):
        if project_id is None:
            return stmt
        return stmt.where(
            (Notification.project_id == project_id) | Notification.project_id.is_(None)
        )

    @staticmethod
    def receipt_join(stmt, user_id: uuid.UUID):
        return stmt.outerjoin(
            NotificationReceipt,
            and_(
                NotificationReceipt.notification_id == Notification.id,
                NotificationReceipt.user_id == user_id,
            ),
        ).where(NotificationReceipt.dismissed_at.is_(None))

    @staticmethod
    async def _stamp(
        session: AsyncSession,
        user_id: uuid.UUID,
        ids,
        *,
        dismiss: bool,
    ) -> int:
        now = utc_now()
        values = select(
            Notification.id,
            literal(user_id, type_=Uuid),
            literal(now, type_=DateTime(timezone=True)),
            literal(now if dismiss else None, type_=DateTime(timezone=True)),
        ).where(Notification.id.in_(ids))
        stmt = insert(NotificationReceipt).from_select(
            ["notification_id", "user_id", "read_at", "dismissed_at"], values
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["notification_id", "user_id"],
            set_={
                "read_at": func.coalesce(NotificationReceipt.read_at, now),
                **({"dismissed_at": now} if dismiss else {}),
            },
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount or 0

    @staticmethod
    async def mark_as_read(
        session: AsyncSession, notification_id: int, user_id: uuid.UUID
    ) -> bool:
        return (
            await NotificationManager._stamp(
                session, user_id, [notification_id], dismiss=False
            )
            > 0
        )

    @staticmethod
    async def mark_all_as_read(
        session: AsyncSession, user_id: uuid.UUID, project_id: uuid.UUID | None = None
    ) -> int:
        unread = NotificationManager.receipt_join(
            NotificationManager.in_scope(select(Notification.id), project_id), user_id
        ).where(NotificationReceipt.read_at.is_(None))
        return await NotificationManager._stamp(session, user_id, unread, dismiss=False)

    @staticmethod
    async def dismiss(
        session: AsyncSession, notification_id: int, user_id: uuid.UUID
    ) -> bool:
        return (
            await NotificationManager._stamp(
                session, user_id, [notification_id], dismiss=True
            )
            > 0
        )

    @staticmethod
    async def dismiss_all(
        session: AsyncSession, user_id: uuid.UUID, project_id: uuid.UUID | None = None
    ) -> int:
        shown = NotificationManager.receipt_join(
            NotificationManager.in_scope(select(Notification.id), project_id), user_id
        )
        return await NotificationManager._stamp(session, user_id, shown, dismiss=True)
