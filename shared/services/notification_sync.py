import logging
from datetime import timedelta

from sqlalchemy.orm import Session

from shared.enums.notification import NotificationSeverity, NotificationType
from shared.enums.sse import SSEChannel, SSEEventType
from shared.models.notification import Notification, NotificationMetadata
from shared.services.event_publisher import SyncEventPublisher
from shared.utils.datetime import utc_now

logger = logging.getLogger(__name__)

NOTIFICATION_EXPIRY_DAYS = 7


class SyncNotificationPublisher:
    """Publish notifications from Celery workers (sync context)."""

    def __init__(self, redis_url: str) -> None:
        self._event_publisher = SyncEventPublisher(redis_url)

    def publish(
        self,
        session: Session,
        type: NotificationType,
        severity: NotificationSeverity,
        title: str,
        message: str,
        metadata: NotificationMetadata | dict | None = None,
    ) -> Notification:
        if isinstance(metadata, NotificationMetadata):
            metadata_dict = metadata.model_dump(exclude_none=True)
        elif isinstance(metadata, dict):
            validated = NotificationMetadata(**metadata)
            metadata_dict = validated.model_dump(exclude_none=True)
        else:
            metadata_dict = {}

        now = utc_now()

        notification = Notification(
            type=type,
            severity=severity,
            title=title[:200],
            message=message,
            notification_metadata=metadata_dict,
            created_at=now,
            expires_at=(now + timedelta(days=NOTIFICATION_EXPIRY_DAYS)).replace(
                tzinfo=None
            ),
        )

        session.add(notification)
        session.commit()
        session.refresh(notification)

        self._event_publisher.publish(
            channel=SSEChannel.BROADCAST,
            event_type=SSEEventType.NOTIFICATION,
            data={
                "id": notification.id,
                "type": notification.type.value,
                "severity": notification.severity.value,
                "title": notification.title,
                "message": notification.message,
                "notification_metadata": notification.notification_metadata,
                "is_read": notification.is_read,
                "created_at": notification.created_at.isoformat(),
            },
        )

        logger.info(
            "Published notification: %s/%s - %s", type.value, severity.value, title
        )

        return notification
