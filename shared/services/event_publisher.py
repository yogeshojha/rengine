import json
import logging
from typing import Any

from shared.redis import async_client, sync_client

logger = logging.getLogger(__name__)

REDIS_SSE_CHANNEL = "rengine:sse_events"


def _message(channel: str, event_type: str, data: dict[str, Any]) -> str:
    return json.dumps(
        {"channel": channel, "event_type": event_type, "data": data}, default=str
    )


class SyncEventPublisher:
    def publish(
        self,
        channel: str,
        event_type: str,
        data: dict[str, Any],
    ) -> bool:
        try:
            sync_client().publish(
                REDIS_SSE_CHANNEL, _message(channel, event_type, data)
            )
            return True
        except Exception:
            logger.exception(
                "Failed to publish event to Redis: channel=%s type=%s",
                channel,
                event_type,
            )
            return False


async def publish_async(channel: str, event_type: str, data: dict[str, Any]) -> bool:
    try:
        await async_client().publish(
            REDIS_SSE_CHANNEL, _message(channel, event_type, data)
        )
        return True
    except Exception:
        logger.exception(
            "Failed to publish event to Redis: channel=%s type=%s",
            channel,
            event_type,
        )
        return False
