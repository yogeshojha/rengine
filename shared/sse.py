import asyncio
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


class SSEManager:
    _instance: "SSEManager | None" = None

    def __new__(cls) -> "SSEManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        self._subscriptions: dict[str, set[asyncio.Queue]] = {}

        self._queue_channels: dict[int, set[str]] = {}

        self._lock = asyncio.Lock()
        self._max_connections = 1000
        self._initialized = True

    async def subscribe(self, queue: asyncio.Queue, channels: list[str]) -> None:
        async with self._lock:
            queue_id = id(queue)
            self._queue_channels[queue_id] = set(channels)
            for channel in channels:
                if channel not in self._subscriptions:
                    self._subscriptions[channel] = set()
                self._subscriptions[channel].add(queue)

        logger.info(
            "SSE client subscribed to %d channel(s): %s | total connections: %d",
            len(channels),
            ", ".join(channels),
            len(self._queue_channels),
        )

    async def unsubscribe(self, queue: asyncio.Queue) -> None:
        async with self._lock:
            queue_id = id(queue)
            channels = self._queue_channels.pop(queue_id, set())
            for channel in channels:
                if channel in self._subscriptions:
                    self._subscriptions[channel].discard(queue)
                    if not self._subscriptions[channel]:
                        del self._subscriptions[channel]

        with suppress(asyncio.QueueEmpty):
            while not queue.empty():
                queue.get_nowait()

        logger.info(
            "SSE client unsubscribed from %d channel(s) | total connections: %d",
            len(channels),
            len(self._queue_channels),
        )

    async def publish(
        self,
        channel: str,
        event_type: str,
        data: dict[str, Any],
    ) -> int:
        subscribers = self._subscriptions.get(channel, set()).copy()
        if not subscribers:
            return 0

        message = self._format_message(channel, event_type, data)
        return await self._deliver(message, subscribers)

    async def publish_multi(
        self,
        channels: list[str],
        event_type: str,
        data: dict[str, Any],
    ) -> int:
        seen: set[asyncio.Queue] = set()
        for channel in channels:
            seen |= self._subscriptions.get(channel, set())

        if not seen:
            return 0

        message = self._format_message(channels[0], event_type, data)
        return await self._deliver(message, seen)

    @asynccontextmanager
    async def stream(self, channels: list[str]) -> AsyncIterator[asyncio.Queue]:
        if len(self._queue_channels) >= self._max_connections:
            msg = "Maximum SSE connections reached"
            raise ConnectionError(msg)

        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        await self.subscribe(queue, channels)
        try:
            yield queue
        finally:
            await self.unsubscribe(queue)

    async def _deliver(self, message: str, subscribers: set[asyncio.Queue]) -> int:
        dead: set[asyncio.Queue] = set()
        delivered = 0

        for queue in subscribers:
            try:
                queue.put_nowait(message)
                delivered += 1
            except asyncio.QueueFull:
                logger.warning("SSE queue full — dropping stale connection")
                dead.add(queue)

        if dead:
            await self._cleanup(dead)

        return delivered

    async def _cleanup(self, dead: set[asyncio.Queue]) -> None:
        async with self._lock:
            for queue in dead:
                queue_id = id(queue)
                channels = self._queue_channels.pop(queue_id, set())
                for channel in channels:
                    if channel in self._subscriptions:
                        self._subscriptions[channel].discard(queue)
                        if not self._subscriptions[channel]:
                            del self._subscriptions[channel]

    @staticmethod
    def _format_message(channel: str, event_type: str, data: dict[str, Any]) -> str:
        payload = {
            "channel": channel,
            "type": event_type,
            "data": data,
            "ts": datetime.now(UTC).isoformat(),
        }
        json_data = json.dumps(payload, default=str)
        return f"event: message\ndata: {json_data}\n\n"

    def get_active_connections(self) -> int:
        return len(self._queue_channels)

    def get_channel_stats(self) -> dict[str, int]:
        return {ch: len(subs) for ch, subs in self._subscriptions.items()}


sse_manager = SSEManager()
