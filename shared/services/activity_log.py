from __future__ import annotations

import uuid

from shared.config import BaseAppSettings
from shared.enums.activity import ActivityEvent, ActivityLevel
from shared.enums.sse import SSEChannel, SSEEventType
from shared.logging import get_logger
from shared.models.activity_log import ActivityLog
from shared.models.target import Target
from shared.services.event_publisher import SyncEventPublisher
from shared.sse import sse_manager
from shared.utils.coerce import safe_uuid

logger = get_logger(__name__)

_sync_publisher = None


def _get_sync_publisher():
    global _sync_publisher  # noqa: PLW0603
    if _sync_publisher is None:
        settings = BaseAppSettings()
        _sync_publisher = SyncEventPublisher(settings.redis_url)
    return _sync_publisher


def _entry_to_sse_payload(entry: ActivityLog) -> dict:
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
        "scan_id": str(entry.scan_id) if entry.scan_id else None,
        "target_value": entry.target_value,
    }


class ActivityLogService:
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
        scan_id: uuid.UUID | str | None = None,
        target_value: str | None = None,
    ) -> ActivityLog:
        if target_id and not target_value:
            target_value = self._resolve_target_value_sync(target_id)
        entry = self._build_entry(
            event=event,
            title=title,
            description=description,
            level=level,
            project_id=project_id,
            target_id=target_id,
            user_id=user_id,
            scan_id=scan_id,
            target_value=target_value,
        )

        self._session.add(entry)
        self._session.flush()

        logger.info("Activity logged: %s - %s", event.value, title[:80])

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
        scan_id: uuid.UUID | str | None = None,
        target_value: str | None = None,
    ) -> ActivityLog:
        if target_id and not target_value:
            target_value = await self._resolve_target_value_async(target_id)
        entry = self._build_entry(
            event=event,
            title=title,
            description=description,
            level=level,
            project_id=project_id,
            target_id=target_id,
            user_id=user_id,
            scan_id=scan_id,
            target_value=target_value,
        )

        self._session.add(entry)
        await self._session.flush()

        logger.info("Activity logged: %s - %s", event.value, title[:80])

        if entry.project_id:
            await self._publish_async(entry)

        return entry

    def _resolve_target_value_sync(self, target_id: uuid.UUID | str) -> str | None:
        tid = safe_uuid(target_id)
        if tid is None:
            return None
        target = self._session.get(Target, tid)
        return target.target_value if target else None

    async def _resolve_target_value_async(
        self, target_id: uuid.UUID | str
    ) -> str | None:
        tid = safe_uuid(target_id)
        if tid is None:
            return None
        target = await self._session.get(Target, tid)
        return target.target_value if target else None

    @staticmethod
    def _publish_sync(entry: ActivityLog) -> None:
        try:
            publisher = _get_sync_publisher()
            publisher.publish(
                channel=SSEChannel.project(str(entry.project_id)),
                event_type=SSEEventType.ACTIVITY,
                data=_entry_to_sse_payload(entry),
            )
        except Exception as e:
            logger.warning("Failed to publish activity to SSE: %s", e)

    @staticmethod
    async def _publish_async(entry: ActivityLog) -> None:
        try:
            await sse_manager.publish(
                channel=SSEChannel.project(str(entry.project_id)),
                event_type=SSEEventType.ACTIVITY,
                data=_entry_to_sse_payload(entry),
            )
        except Exception as e:
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
        scan_id: uuid.UUID | str | None = None,
        target_value: str | None = None,
    ) -> ActivityLog:
        return ActivityLog(
            level=level,
            event_type=event,
            title=title[:200],
            description=description[:2000] if description else None,
            project_id=safe_uuid(project_id),
            target_id=safe_uuid(target_id),
            user_id=safe_uuid(user_id),
            scan_id=safe_uuid(scan_id),
            target_value=target_value[:500] if target_value else None,
        )
