import asyncio
import contextlib
import json

import redis.asyncio as aioredis

from shared.logging import get_logger
from shared.services.event_publisher import REDIS_SSE_CHANNEL
from shared.sse import sse_manager

logger = get_logger(__name__)


class RedisSSEBridge:
    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._task = asyncio.create_task(self._listen())
        logger.info("Redis SSE bridge started")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            logger.info("Redis SSE bridge stopped")

    async def _listen(self) -> None:
        while True:
            client = None
            pubsub = None
            try:
                client = aioredis.from_url(self._redis_url)
                pubsub = client.pubsub()
                await pubsub.subscribe(REDIS_SSE_CHANNEL)
                logger.info("Subscribed to Redis channel: %s", REDIS_SSE_CHANNEL)

                async for message in pubsub.listen():
                    if message["type"] != "message":
                        continue
                    try:
                        payload = json.loads(message["data"])
                        await sse_manager.publish(
                            channel=payload["channel"],
                            event_type=payload["event_type"],
                            data=payload["data"],
                        )
                    except KeyError:
                        logger.warning(
                            "Malformed Redis SSE message (missing channel/event_type/data): %s",
                            message["data"],
                        )
                    except Exception:
                        logger.exception("Failed to process Redis SSE event")

            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Redis SSE bridge connection lost, reconnecting in 5s")
                await asyncio.sleep(5)
            finally:
                if pubsub:
                    with contextlib.suppress(Exception):
                        await pubsub.unsubscribe(REDIS_SSE_CHANNEL)
                        await pubsub.aclose()
                if client:
                    with contextlib.suppress(Exception):
                        await client.aclose()
