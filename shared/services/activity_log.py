"""Activity log service for recording audit trails and feed events.

Every log entry is automatically published to SSE so the frontend
activity feed updates in real time.

Usage:
    Sync (Celery workers):
        service = ActivityLogService(session)
        service.log(
            event=ActivityEvent.TARGET_ENRICHMENT_WHOIS_COMPLETED,
            title=f"WHOIS completed",
            target_id=target.id,
            project_id=target.project_id,
        )

    Async (FastAPI routes):
        service = ActivityLogService(session)
        await service.log_async(
            event=ActivityEvent.TARGET_CREATED,
            title="Target added",
            target_id=target.id,
            project_id=target.project_id,
            user_id=user_id,
        )
"""

from __future__ import annotations

import uuid

from shared.config import BaseSettings_
from shared.enums.activity import ActivityEvent, ActivityLevel
from shared.enums.sse import SSEChannel, SSEEventType
from shared.logging import get_logger
from shared.models.activity_log import ActivityLog
from shared.services.event_publisher import SyncEventPublisher
from shared.sse import sse_manager
from shared.utils.coerce import safe_uuid

logger = get_logger(__name__)

_sync_publisher = None


def _get_sync_publisher():
    """Get or create a cached SyncEventPublisher (one per process)."""
    global _sync_publisher  # noqa: PLW0603
    if _sync_publisher is None:
        settings = BaseSettings_()
        _sync_publisher = SyncEventPublisher(settings.redis_url)
    return _sync_publisher


def _entry_to_sse_payload(entry: ActivityLog) -> dict:
    """Convert an ActivityLog to the SSE data dict."""
    return {
        "id": str(entry.id),
        "timestamp": entry.timestamp.isoformat(),
        "level": entry.level.value
        if hasattr(entry.level, "value")
        else str(entry.level),
        "event_type": entry.event_type.value
        if hasattr(entry.event_type, "value")
        else str(entry.event_type),
        "title": entry.title,
        "description": entry.description,
        "project_id": str(entry.project_id) if entry.project_id else None,
        "target_id": str(entry.target_id) if entry.target_id else None,
        "user_id": str(entry.user_id) if entry.user_id else None,
    }


class ActivityLogService:
    """Unified activity log service for sync and async contexts."""

    def __init__(self, session) -> None:
        self._session = session

    def log(
        self,
        *,
        event: ActivityEvent,
        title: str,
        description: str | None = None,
        level: ActivityLevel = ActivityLevel.INFO,
        project_id: uuid.UUID | str | None = None,
        target_id: uuid.UUID | str | None = None,
        user_id: uuid.UUID | str | None = None,
    ) -> ActivityLog:
        """Record an activity log entry (sync) and publish to SSE via Redis."""
        entry = self._build_entry(
            event=event,
            title=title,
            description=description,
            level=level,
            project_id=project_id,
            target_id=target_id,
            user_id=user_id,
        )

        self._session.add(entry)
        self._session.flush()

        logger.info("Activity logged: %s - %s", event.value, title[:80])

        # Publish to SSE via Redis (sync path for Celery workers)
        if entry.project_id:
            self._publish_sync(entry)

        return entry

    async def log_async(
        self,
        *,
        event: ActivityEvent,
        title: str,
        description: str | None = None,
        level: ActivityLevel = ActivityLevel.INFO,
        project_id: uuid.UUID | str | None = None,
        target_id: uuid.UUID | str | None = None,
        user_id: uuid.UUID | str | None = None,
    ) -> ActivityLog:
        """Record an activity log entry (async) and publish to SSE directly."""
        entry = self._build_entry(
            event=event,
            title=title,
            description=description,
            level=level,
            project_id=project_id,
            target_id=target_id,
            user_id=user_id,
        )

        self._session.add(entry)
        await self._session.flush()

        logger.info("Activity logged: %s - %s", event.value, title[:80])

        # Publish to SSE directly (async path for FastAPI)
        if entry.project_id:
            await self._publish_async(entry)

        return entry

    @staticmethod
    def _publish_sync(entry: ActivityLog) -> None:
        """Push activity event to SSE via Redis (for Celery/sync contexts)."""
        try:
            publisher = _get_sync_publisher()
            publisher.publish(
                channel=SSEChannel.project(str(entry.project_id)),
                event_type=SSEEventType.ACTIVITY,
                data=_entry_to_sse_payload(entry),
            )
        except Exception as e:
            # SSE publish failure should never break activity logging
            logger.warning("Failed to publish activity to SSE: %s", e)

    @staticmethod
    async def _publish_async(entry: ActivityLog) -> None:
        """Push activity event to SSE directly (for FastAPI/async contexts)."""
        try:
            await sse_manager.publish(
                channel=SSEChannel.project(str(entry.project_id)),
                event_type=SSEEventType.ACTIVITY,
                data=_entry_to_sse_payload(entry),
            )
        except Exception as e:
            # SSE publish failure should never break activity logging
            logger.warning("Failed to publish activity to SSE: %s", e)

    @staticmethod
    def _build_entry(
        *,
        event: ActivityEvent,
        title: str,
        description: str | None,
        level: ActivityLevel,
        project_id: uuid.UUID | str | None,
        target_id: uuid.UUID | str | None,
        user_id: uuid.UUID | str | None,
    ) -> ActivityLog:
        """Build an ActivityLog instance without persisting."""
        return ActivityLog(
            level=level,
            event_type=event,
            title=title[:200],
            description=description[:2000] if description else None,
            project_id=safe_uuid(project_id),
            target_id=safe_uuid(target_id),
            user_id=safe_uuid(user_id),
        )
