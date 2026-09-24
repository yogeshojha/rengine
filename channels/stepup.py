"""Authenticator step-up for commands above read."""

from __future__ import annotations

import json
import re

from shared.definitions.channels import (
    OTP_ATTEMPT_LIMIT,
    OTP_ATTEMPT_WINDOW,
    STEP_UP_GRACE_SECONDS,
    STEP_UP_PENDING_SECONDS,
)
from shared.redis import async_client

PENDING_KEY = "channels:stepup:pending:{channel}:{external_id}"
GRACE_KEY = "channels:stepup:grace:{channel}:{external_id}"
ATTEMPT_KEY = "channels:stepup:attempts:{channel}:{external_id}"

_TOTP_RE = re.compile(r"^\d{6}$")
_BACKUP_RE = re.compile(r"^[0-9a-f]{4}-[0-9a-f]{4}$", re.I)


def looks_like_code(text: str) -> bool:
    value = text.strip()
    return bool(_TOTP_RE.match(value) or _BACKUP_RE.match(value))


async def hold(channel: str, external_id: str, command: str) -> None:
    key = PENDING_KEY.format(channel=channel, external_id=external_id)
    await async_client().set(
        key, json.dumps({"command": command}), ex=STEP_UP_PENDING_SECONDS
    )


async def take(channel: str, external_id: str) -> str | None:
    redis = async_client()
    key = PENDING_KEY.format(channel=channel, external_id=external_id)
    raw = await redis.get(key)
    if raw is None:
        return None
    await redis.delete(key)
    try:
        return str(json.loads(raw)["command"])
    except (ValueError, KeyError, TypeError):
        return None


async def in_grace(channel: str, external_id: str) -> bool:
    key = GRACE_KEY.format(channel=channel, external_id=external_id)
    return await async_client().exists(key) == 1


async def grace_remaining(channel: str, external_id: str) -> int:
    key = GRACE_KEY.format(channel=channel, external_id=external_id)
    ttl = await async_client().ttl(key)
    return max(0, int(ttl or 0))


async def grant(channel: str, external_id: str) -> None:
    key = GRACE_KEY.format(channel=channel, external_id=external_id)
    await async_client().set(key, "1", ex=STEP_UP_GRACE_SECONDS)


async def clear_grace(channel: str, external_id: str) -> None:
    await async_client().delete(
        GRACE_KEY.format(channel=channel, external_id=external_id)
    )


async def attempts_exhausted(channel: str, external_id: str) -> int:
    """Seconds until the next attempt is allowed, 0 when allowed now."""
    redis = async_client()
    key = ATTEMPT_KEY.format(channel=channel, external_id=external_id)
    raw = await redis.get(key)
    if raw is None or int(raw) < OTP_ATTEMPT_LIMIT:
        return 0
    ttl = await redis.ttl(key)
    return max(1, int(ttl or 0))


async def note_failure(channel: str, external_id: str) -> None:
    from app.core.ratelimit import record_failure  # noqa: PLC0415

    key = ATTEMPT_KEY.format(channel=channel, external_id=external_id)
    await record_failure(key, window_seconds=OTP_ATTEMPT_WINDOW)


async def clear_failures(channel: str, external_id: str) -> None:
    from app.core.ratelimit import clear_failures as clear  # noqa: PLC0415

    await clear(ATTEMPT_KEY.format(channel=channel, external_id=external_id))
