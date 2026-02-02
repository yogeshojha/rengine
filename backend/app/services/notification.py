import logging
from datetime import UTC, datetime

from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.sse import connection_manager
from app.enums.notification import NotificationSeverity, NotificationType
from app.models.notification import Notification, NotificationMetadata

logger = logging.getLogger(__name__)


class NotificationManager:
    @staticmethod
    async def publish(
        session: AsyncSession,
        type: NotificationType,
        severity: NotificationSeverity,
        title: str,
        message: str,
        metadata: NotificationMetadata | dict | None = None,
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
            metadata=metadata_dict,
        )

        session.add(notification)

        if commit:
            await session.commit()
            await session.refresh(notification)

        await connection_manager.broadcast(
            event_type="notification",
            data={
                "id": notification.id,
                "type": notification.type.value,
                "severity": notification.severity.value,
                "title": notification.title,
                "message": notification.message,
                "metadata": notification.notification_metadata,
                "is_read": notification.is_read,
                "created_at": notification.created_at.isoformat(),
            },
        )

        logger.info(f"Published notification: {type.value}/{severity.value} - {title}")

        return notification

    @staticmethod
    async def mark_as_read(
        session: AsyncSession,
        notification_id: int,
        commit: bool = True,
    ) -> bool:
        result = await session.execute(
            update(Notification)
            .where(Notification.id == notification_id, not Notification.is_read)
            .values(is_read=True)
        )

        if commit:
            await session.commit()

        return result.rowcount > 0

    @staticmethod
    async def mark_all_as_read(
        session: AsyncSession,
        commit: bool = True,
    ) -> int:
        result = await session.execute(
            update(Notification).where(not Notification.is_read).values(is_read=True)
        )

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
        commit: bool = True,
    ) -> int:
        result = await session.execute(delete(Notification))

        if commit:
            await session.commit()

        return result.rowcount

    @staticmethod
    async def cleanup_expired(
        session: AsyncSession,
        commit: bool = True,
    ) -> int:
        now = datetime.now(UTC).replace(tzinfo=None)
        result = await session.execute(
            delete(Notification).where(Notification.expires_at < now)
        )

        if commit:
            await session.commit()

        deleted_count = result.rowcount
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} expired notifications")

        return deleted_count
