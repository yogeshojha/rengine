"""Sync notification publisher."""

import json
import logging
from datetime import timedelta

import redis
from sqlalchemy.orm import Session

from shared.enums.notification import NotificationSeverity, NotificationType
from shared.models.notification import Notification, NotificationMetadata
from shared.utils.datetime import utc_now

logger = logging.getLogger(__name__)

REDIS_NOTIFICATION_CHANNEL = "rengine:notifications"
NOTIFICATION_EXPIRY_DAYS = 7


class SyncNotificationPublisher:
    """Publish notifications from Celery workers (sync context)."""

    def __init__(self, redis_url: str) -> None:
        self._redis = redis.from_url(redis_url)

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

        self._publish_to_redis(notification)

        logger.info(
            "Published notification: %s/%s - %s", type.value, severity.value, title
        )

        return notification

    def _publish_to_redis(self, notification: Notification) -> None:
        """Publish to Redis so the API's listener can broadcast via SSE."""
        try:
            payload = {
                "id": notification.id,
                "type": notification.type.value,
                "severity": notification.severity.value,
                "title": notification.title,
                "message": notification.message,
                "notification_metadata": notification.notification_metadata,
                "is_read": notification.is_read,
                "created_at": notification.created_at.isoformat(),
            }
            self._redis.publish(
                REDIS_NOTIFICATION_CHANNEL,
                json.dumps(payload, default=str),
            )
        except Exception:
            logger.exception("Failed to publish notification to Redis")
