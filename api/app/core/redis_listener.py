"""Redis to SSE bridge for celery worker-originated notifications."""

import asyncio
import contextlib
import json
import logging

import redis.asyncio as aioredis

from app.core.sse import connection_manager
from shared.services.notification_sync import REDIS_NOTIFICATION_CHANNEL

logger = logging.getLogger(__name__)


class RedisNotificationListener:
    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._task = asyncio.create_task(self._listen())
        logger.info("Redis notification listener started")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            logger.info("Redis notification listener stopped")

    async def _listen(self) -> None:
        while True:
            client = None
            pubsub = None
            try:
                client = aioredis.from_url(self._redis_url)
                pubsub = client.pubsub()
                await pubsub.subscribe(REDIS_NOTIFICATION_CHANNEL)
                logger.info(
                    "Subscribed to Redis channel: %s", REDIS_NOTIFICATION_CHANNEL
                )

                async for message in pubsub.listen():
                    if message["type"] != "message":
                        continue
                    try:
                        data = json.loads(message["data"])
                        await connection_manager.broadcast(
                            event_type="notification",
                            data=data,
                        )
                    except Exception:
                        logger.exception("Failed to process Redis notification")

            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Redis listener connection lost, reconnecting in 5s")
                await asyncio.sleep(5)
            finally:
                if pubsub:
                    with contextlib.suppress(Exception):
                        await pubsub.unsubscribe(REDIS_NOTIFICATION_CHANNEL)
                        await pubsub.aclose()
                if client:
                    with contextlib.suppress(Exception):
                        await client.aclose()
