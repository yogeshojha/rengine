"""Sync event publisher for pushing events from Celery workers to SSE via Redis."""

import json
import logging
from typing import Any

import redis

logger = logging.getLogger(__name__)

REDIS_SSE_CHANNEL = "rengine:sse_events"


class SyncEventPublisher:
    def __init__(self, redis_url: str) -> None:
        self._redis = redis.from_url(redis_url)

    def publish(
        self,
        channel: str,
        event_type: str,
        data: dict[str, Any],
    ) -> bool:
        """Publish an event to the Redis SSE bridge.

        Args:
            channel: SSE channel to deliver to (e.g. "broadcast", "project:{id}")
            event_type: Event type within the channel (e.g. "notification", "activity")
            data: Event payload

        Returns:
            True if published successfully, False otherwise.
        """
        try:
            payload = {
                "channel": channel,
                "event_type": event_type,
                "data": data,
            }
            self._redis.publish(
                REDIS_SSE_CHANNEL,
                json.dumps(payload, default=str),
            )
            return True
        except Exception:
            logger.exception(
                "Failed to publish event to Redis: channel=%s type=%s",
                channel,
                event_type,
            )
            return False
