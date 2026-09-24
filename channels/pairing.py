"""Pairing codes for unknown chats."""

from __future__ import annotations

import contextlib
import json
import secrets
from datetime import timedelta

from shared.definitions.channels import (
    PAIRING_ALPHABET,
    PAIRING_CODE_LENGTH,
    PAIRING_CODE_TTL,
    PENDING_PAIRINGS_MAX,
)
from shared.logging import get_logger
from shared.redis import async_client
from shared.utils.datetime import utc_now

logger = get_logger(__name__)

CODE_KEY = "channels:pair:{channel}:{code}"
CHAT_KEY = "channels:pair:chat:{channel}:{external_id}"
INDEX_KEY = "channels:pair:index:{channel}"


def new_code() -> str:
    body = "".join(secrets.choice(PAIRING_ALPHABET) for _ in range(PAIRING_CODE_LENGTH))
    half = PAIRING_CODE_LENGTH // 2
    return f"{body[:half]}-{body[half:]}"


def normalise(code: str) -> str:
    raw = "".join(c for c in code.upper() if c.isalnum())
    half = PAIRING_CODE_LENGTH // 2
    return f"{raw[:half]}-{raw[half:]}" if len(raw) == PAIRING_CODE_LENGTH else raw


async def request(
    channel: str,
    *,
    external_id: str,
    display: str,
    username: str | None,
    first_name: str | None,
) -> tuple[str | None, bool]:
    """Return (code, created). The code is None when the queue is full."""
    redis = async_client()
    chat_key = CHAT_KEY.format(channel=channel, external_id=external_id)
    existing = await redis.get(chat_key)
    if existing:
        return existing, False

    index = INDEX_KEY.format(channel=channel)
    if await redis.scard(index) >= PENDING_PAIRINGS_MAX:
        await _prune(channel)
        if await redis.scard(index) >= PENDING_PAIRINGS_MAX:
            return None, False

    code = new_code()
    now = utc_now()
    payload = {
        "code": code,
        "external_id": external_id,
        "display": display,
        "username": username,
        "first_name": first_name,
        "requested_at": now.isoformat(),
        "expires_at": (now + timedelta(seconds=PAIRING_CODE_TTL)).isoformat(),
    }
    pipe = redis.pipeline(transaction=True)
    pipe.set(
        CODE_KEY.format(channel=channel, code=code),
        json.dumps(payload),
        ex=PAIRING_CODE_TTL,
    )
    pipe.set(chat_key, code, ex=PAIRING_CODE_TTL)
    pipe.sadd(index, code)
    pipe.expire(index, PAIRING_CODE_TTL * 2)
    await pipe.execute()
    return code, True


async def pending(channel: str) -> list[dict]:
    redis = async_client()
    index = INDEX_KEY.format(channel=channel)
    codes = sorted(await redis.smembers(index))
    if not codes:
        return []
    rows = await redis.mget([CODE_KEY.format(channel=channel, code=c) for c in codes])
    live: list[dict] = []
    stale: list[str] = []
    for code, raw in zip(codes, rows, strict=False):
        if raw is None:
            stale.append(code)
            continue
        with contextlib.suppress(ValueError):
            live.append(json.loads(raw))
    if stale:
        with contextlib.suppress(Exception):
            await redis.srem(index, *stale)
    return sorted(live, key=lambda r: r.get("requested_at", ""))


async def take(channel: str, code: str) -> dict | None:
    """Remove a pending request and return it."""
    redis = async_client()
    key = CODE_KEY.format(channel=channel, code=normalise(code))
    raw = await redis.getdel(key)
    if raw is None:
        return None
    try:
        payload = json.loads(raw)
    except ValueError:
        payload = None
    pipe = redis.pipeline(transaction=True)
    pipe.srem(INDEX_KEY.format(channel=channel), normalise(code))
    if payload:
        pipe.delete(
            CHAT_KEY.format(channel=channel, external_id=payload["external_id"])
        )
    await pipe.execute()
    return payload


async def forget(channel: str, external_id: str) -> None:
    redis = async_client()
    chat_key = CHAT_KEY.format(channel=channel, external_id=external_id)
    code = await redis.get(chat_key)
    pipe = redis.pipeline(transaction=True)
    pipe.delete(chat_key)
    if code:
        pipe.delete(CODE_KEY.format(channel=channel, code=code))
        pipe.srem(INDEX_KEY.format(channel=channel), code)
    await pipe.execute()


async def _prune(channel: str) -> None:
    await pending(channel)
