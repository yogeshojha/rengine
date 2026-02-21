"""Activity log service for recording audit trails and feed events.

Usage:
    Sync:
        service = ActivityLogService(session)
        service.log(
            event=ActivityEvent.TARGET_ENRICHMENT_WHOIS_COMPLETED,
            title=f"WHOIS completed for {target.target_value}",
            target_id=target.id,
            project_id=target.project_id,
        )

    Async:
        service = ActivityLogService(session)
        await service.log_async(
            event=ActivityEvent.TARGET_CREATED,
            title=f"Target added: {target.target_value}",
            target_id=target.id,
            project_id=target.project_id,
            user_id=user_id,
        )
"""

import uuid

from shared.enums.activity import ActivityEvent, ActivityLevel
from shared.logging import get_logger
from shared.models.activity_log import ActivityLog
from shared.utils.coerce import safe_uuid

logger = get_logger("shared.services.activity_log")


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
        """Record an activity log entry (sync)."""
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
        """Record an activity log entry (async)."""
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

        return entry

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
