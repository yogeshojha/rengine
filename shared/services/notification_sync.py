import logging
import uuid

from sqlalchemy.orm import Session

from shared.enums.notification import NotificationSeverity, NotificationType
from shared.enums.sse import SSEChannel, SSEEventType
from shared.models.notification import Notification, NotificationMetadata
from shared.services.event_publisher import SyncEventPublisher
from shared.utils.datetime import utc_now

logger = logging.getLogger(__name__)


class SyncNotificationPublisher:
    def __init__(self) -> None:
        self._event_publisher = SyncEventPublisher()

    def publish(
        self,
        session: Session,
        type: NotificationType,
        severity: NotificationSeverity,
        title: str,
        message: str,
        metadata: NotificationMetadata | dict | None = None,
        project_id: uuid.UUID | str | None = None,
        channel_ids=None,
        attach: str | None = None,
        dispatch: bool = True,
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
            project_id=uuid.UUID(str(project_id)) if project_id else None,
            created_at=now,
        )

        session.add(notification)
        session.commit()
        session.refresh(notification)

        self._event_publisher.publish(
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

        logger.info(
            "Published notification: %s/%s - %s", type.value, severity.value, title
        )

        if not dispatch:
            return notification
        try:
            from shared.services.notifier import dispatch_sync  # noqa: PLC0415

            dispatch_sync(
                session,
                type,
                severity,
                title,
                message,
                channel_ids=channel_ids,
                attach=attach,
                metadata=metadata_dict,
            )
        except Exception as exc:
            logger.warning("External notification dispatch failed: %s", exc)

        return notification
