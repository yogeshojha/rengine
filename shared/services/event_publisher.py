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
