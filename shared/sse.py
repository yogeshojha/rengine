import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from typing import Any

from shared.logging import get_logger
from shared.utils.datetime import utc_now

logger = get_logger(__name__)

STREAM_CLOSED = None

MAX_STREAMS_PER_OWNER = 20


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

        self._owner_streams: dict[str, int] = {}

        self._lock = asyncio.Lock()
        self._max_connections = 1000
        self._initialized = True

    def at_capacity(self) -> bool:
        return len(self._queue_channels) >= self._max_connections

    def owner_at_capacity(self, owner: str) -> bool:
        return self._owner_streams.get(owner, 0) >= MAX_STREAMS_PER_OWNER

    async def subscribe(self, queue: asyncio.Queue, channels: list[str]) -> None:
        async with self._lock:
            queue_id = id(queue)
            self._queue_channels[queue_id] = set(channels)
            for channel in channels:
                if channel not in self._subscriptions:
                    self._subscriptions[channel] = set()
                self._subscriptions[channel].add(queue)

        logger.debug(
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

        logger.debug(
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

    @asynccontextmanager
    async def stream(
        self, channels: list[str], owner: str | None = None
    ) -> AsyncIterator[asyncio.Queue]:
        if self.at_capacity():
            msg = "Maximum SSE connections reached"
            raise ConnectionError(msg)
        if owner is not None and self.owner_at_capacity(owner):
            msg = "Maximum SSE connections reached for the owner"
            raise ConnectionError(msg)

        if owner is not None:
            self._owner_streams[owner] = self._owner_streams.get(owner, 0) + 1
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        try:
            await self.subscribe(queue, channels)
            yield queue
        finally:
            await self.unsubscribe(queue)
            if owner is not None:
                left = self._owner_streams.get(owner, 1) - 1
                if left > 0:
                    self._owner_streams[owner] = left
                else:
                    self._owner_streams.pop(owner, None)

    async def _deliver(self, message: str, subscribers: set[asyncio.Queue]) -> int:
        dead: set[asyncio.Queue] = set()
        delivered = 0

        for queue in subscribers:
            try:
                queue.put_nowait(message)
                delivered += 1
            except asyncio.QueueFull:
                logger.warning("SSE queue full, closing the stream")
                with suppress(asyncio.QueueEmpty):
                    while not queue.empty():
                        queue.get_nowait()
                queue.put_nowait(STREAM_CLOSED)
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
            "ts": utc_now().isoformat(),
        }
        json_data = json.dumps(payload, default=str)
        return f"event: message\ndata: {json_data}\n\n"


sse_manager = SSEManager()
