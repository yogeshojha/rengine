import uuid

from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.enums.notification import NotificationSeverity, NotificationType
from shared.enums.sse import SSEChannel, SSEEventType
from shared.logging import get_logger
from shared.models.notification import Notification, NotificationMetadata
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
                "is_read": notification.is_read,
                "created_at": notification.created_at.isoformat(),
            },
        )

        logger.info(f"Published notification: {type.value}/{severity.value} - {title}")

        try:
            from shared.services.notifier import dispatch_async  # noqa: PLC0415

            await dispatch_async(session, type, severity, title, message)
        except Exception as exc:
            logger.warning(f"External notification dispatch failed: {exc}")

        return notification

    @staticmethod
    async def mark_as_read(
        session: AsyncSession,
        notification_id: int,
        commit: bool = True,
    ) -> bool:
        result = await session.execute(
            update(Notification)
            .where(Notification.id == notification_id)
            .values(is_read=True)
        )

        if commit:
            await session.commit()

        return result.rowcount > 0

    @staticmethod
    async def mark_all_as_read(
        session: AsyncSession,
        project_id: uuid.UUID | None = None,
        commit: bool = True,
    ) -> int:
        stmt = update(Notification).where(Notification.is_read.is_(False))
        if project_id is not None:
            stmt = stmt.where(
                (Notification.project_id == project_id)
                | Notification.project_id.is_(None)
            )
        result = await session.execute(stmt.values(is_read=True))

        if commit:
            await session.commit()

        return result.rowcount

    @staticmethod
    async def delete_notification(
        session: AsyncSession,
        notification_id: int,
        commit: bool = True,
    ) -> bool:
        result = await session.execute(
            delete(Notification).where(Notification.id == notification_id)
        )

        if commit:
            await session.commit()

        return result.rowcount > 0

    @staticmethod
    async def clear_all(
        session: AsyncSession,
        project_id: uuid.UUID | None = None,
        commit: bool = True,
    ) -> int:
        stmt = delete(Notification)
        if project_id is not None:
            stmt = stmt.where(
                (Notification.project_id == project_id)
                | Notification.project_id.is_(None)
            )
        result = await session.execute(stmt)

        if commit:
            await session.commit()

        return result.rowcount

    @staticmethod
    async def cleanup_expired(
        session: AsyncSession,
        commit: bool = True,
    ) -> int:
        now = utc_now()
        result = await session.execute(
            delete(Notification).where(Notification.expires_at < now)
        )

        if commit:
            await session.commit()

        deleted_count = result.rowcount
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} expired notifications")

        return deleted_count
