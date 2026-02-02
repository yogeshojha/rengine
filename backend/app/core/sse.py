import asyncio
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime
from typing import Any

from fastapi import Request

logger = logging.getLogger(__name__)


class ConnectionManager:
    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._connections: set[asyncio.Queue] = set()
        self._max_connections = 1000
        self._heartbeat_interval = 30
        self._initialized = True

    async def connect(self, request: Request) -> asyncio.Queue:
        if len(self._connections) >= self._max_connections:
            msg = "Maximum concurrent connections reached"
            raise ConnectionError(msg)

        queue: asyncio.Queue = asyncio.Queue(maxsize=100)

        async with self._lock:
            self._connections.add(queue)

        logger.info(
            f"SSE connection established from {request.client.host if request.client else 'unknown'}. "
            f"Active connections: {len(self._connections)}"
        )
        return queue

    async def disconnect(self, queue: asyncio.Queue):
        async with self._lock:
            self._connections.discard(queue)

        try:
            while not queue.empty():
                queue.get_nowait()
        except asyncio.QueueEmpty:
            pass

        logger.info(
            f"SSE connection closed. Active connections: {len(self._connections)}"
        )

    async def broadcast(self, event_type: str, data: dict[str, Any]):
        if not self._connections:
            return

        message = self._format_sse_message(event_type, data)
        dead_queues = set()

        for queue in self._connections.copy():
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                logger.warning("Queue full, dropping message for connection")
                dead_queues.add(queue)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                dead_queues.add(queue)

        if dead_queues:
            async with self._lock:
                self._connections -= dead_queues

    def _format_sse_message(self, event_type: str, data: dict[str, Any]) -> str:
        json_data = json.dumps(data, default=str)
        return f"event: {event_type}\ndata: {json_data}\n\n"

    async def _send_heartbeat(self, queue: asyncio.Queue):
        heartbeat_msg = self._format_sse_message(
            "heartbeat", {"timestamp": datetime.now(UTC).isoformat()}
        )
        with suppress(asyncio.QueueFull):
            queue.put_nowait(heartbeat_msg)

    @asynccontextmanager
    async def stream(self, request: Request) -> AsyncIterator[asyncio.Queue]:
        queue = await self.connect(request)
        try:
            yield queue
        finally:
            await self.disconnect(queue)

    def get_active_connections_count(self) -> int:
        return len(self._connections)


connection_manager = ConnectionManager()
