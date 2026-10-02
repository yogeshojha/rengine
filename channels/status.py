"""Listener heartbeat and update offset in Redis."""

from __future__ import annotations

import contextlib
import json

from shared.definitions.channels import STATUS_TTL
from shared.logging import get_logger
from shared.redis import async_client

logger = get_logger(__name__)

KEY = "channels:status:{channel}"
OFFSET_KEY = "channels:offset:{channel}:{bot}"


async def publish(channel: str, payload: dict) -> None:
    try:
        await async_client().set(
            KEY.format(channel=channel), json.dumps(payload), ex=STATUS_TTL
        )
    except Exception as exc:
        logger.debug("listener status not written", error=str(exc))


async def read(channel: str) -> dict | None:
    try:
        raw = await async_client().get(KEY.format(channel=channel))
    except Exception as exc:
        logger.debug("listener status unavailable", error=str(exc))
        return None
    if not raw:
        return None
    with contextlib.suppress(ValueError):
        return json.loads(raw)
    return None


async def load_offset(channel: str, bot: str) -> int:
    try:
        raw = await async_client().get(OFFSET_KEY.format(channel=channel, bot=bot))
    except Exception:
        return 0
    return int(raw or 0)


async def save_offset(channel: str, bot: str, offset: int) -> None:
    with contextlib.suppress(Exception):
        await async_client().set(
            OFFSET_KEY.format(channel=channel, bot=bot), str(offset)
        )
