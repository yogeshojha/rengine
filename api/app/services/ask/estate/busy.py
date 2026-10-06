"""One answer at a time per estate thread."""

from __future__ import annotations

import secrets
import uuid

import anyio

from shared.logging import get_logger
from shared.redis import async_client
from shared.services.ai import AIError

logger = get_logger(__name__)

KEY = "ask:turn:{thread_id}"
TURN_SECONDS = 600
BUSY = "An answer is being written in this thread. Ask again when it finishes."
LOCK_DOWN = "The thread lock is unavailable. Check that the redis service is running."


async def claim(thread_id: uuid.UUID) -> str | None:
    """A token while no other answer runs in the thread, else None."""
    token = secrets.token_hex(8)
    try:
        held = await async_client().set(
            KEY.format(thread_id=thread_id), token, nx=True, ex=TURN_SECONDS
        )
    except Exception as exc:
        logger.warning("ask turn lock unavailable", error=str(exc))
        raise AIError(LOCK_DOWN) from exc
    return token if held else None


async def release(thread_id: uuid.UUID, token: str) -> None:
    key = KEY.format(thread_id=thread_id)
    with anyio.CancelScope(shield=True):
        try:
            client = async_client()
            if await client.get(key) == token:
                await client.delete(key)
        except Exception as exc:
            logger.warning("ask turn lock not released", error=str(exc))
