"""Inbound message and channel interface."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import ClassVar

from channels.render import Line, Message, chunk


class DriverError(Exception):
    """A channel refused the request."""

    def __init__(self, description: str):
        super().__init__(description)
        self.description = description


@dataclass(frozen=True)
class Inbound:
    channel: str
    external_id: str
    sender_id: str
    username: str | None
    first_name: str | None
    text: str
    message_id: str | None
    private: bool

    @property
    def display(self) -> str:
        if self.username:
            return f"@{self.username}"
        return (self.first_name or self.external_id).strip()


class Channel(ABC):
    kind: ClassVar[str]
    limit: ClassVar[int]

    @abstractmethod
    async def send(self, external_id: str, message: Message) -> str | None:
        """Send one message and return its id."""

    async def edit(
        self,
        external_id: str,
        message_id: str,  # noqa: ARG002
        message: Message,
    ) -> None:
        await self.send(external_id, message)

    async def delete(self, external_id: str, message_id: str) -> None:  # noqa: ARG002
        return None

    async def reply(self, external_id: str, lines: list[Line]) -> str | None:
        last: str | None = None
        for message in chunk(lines, self.limit):
            last = await self.send(external_id, message)
        return last


class ChatLocks:
    """One lock per chat, dropped once nothing holds or awaits it."""

    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = {}
        self._users: dict[str, int] = {}

    def __len__(self) -> int:
        return len(self._locks)

    @asynccontextmanager
    async def hold(self, key: str) -> AsyncIterator[None]:
        lock = self._locks.setdefault(key, asyncio.Lock())
        self._users[key] = self._users.get(key, 0) + 1
        try:
            async with lock:
                yield
        finally:
            remaining = self._users[key] - 1
            if remaining:
                self._users[key] = remaining
            else:
                del self._users[key]
                del self._locks[key]
