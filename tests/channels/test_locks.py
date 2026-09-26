"""A chat's messages are handled one at a time, and the lock is not kept after."""

from __future__ import annotations

import asyncio

import pytest

from channels.base import ChatLocks

pytestmark = pytest.mark.channels


async def test_one_chat_is_handled_one_message_at_a_time():
    locks = ChatLocks()
    order: list[str] = []

    async def handle(name: str) -> None:
        async with locks.hold("42"):
            order.append(f"{name} in")
            await asyncio.sleep(0)
            order.append(f"{name} out")

    await asyncio.gather(handle("a"), handle("b"))

    assert order == ["a in", "a out", "b in", "b out"]


async def test_a_lock_is_kept_while_another_message_waits():
    locks = ChatLocks()
    entered = asyncio.Event()
    queued = asyncio.Event()
    release = asyncio.Event()

    async def first() -> None:
        async with locks.hold("42"):
            entered.set()
            await release.wait()

    async def second() -> None:
        await entered.wait()
        queued.set()
        async with locks.hold("42"):
            pass

    task = asyncio.create_task(first())
    waiter = asyncio.create_task(second())
    await queued.wait()
    assert len(locks) == 1
    release.set()
    await asyncio.gather(task, waiter)
    assert len(locks) == 0


async def test_an_unknown_sender_leaves_nothing_behind():
    locks = ChatLocks()
    for chat in range(500):
        async with locks.hold(str(chat)):
            pass
    assert len(locks) == 0
