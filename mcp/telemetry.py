"""Live sessions and the recent-call trail. Ephemeral by design: Redis, not a table.

Every write is fail-open — losing a session row must never fail an agent's call.
"""

from __future__ import annotations

import contextlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from shared.logging import get_logger
from shared.utils.datetime import utc_now

logger = get_logger(__name__)

SESSION_KEY = "mcp:session:{token_id}:{client}"
SESSION_INDEX = "mcp:sessions"
CALLS_KEY = "mcp:calls"
COUNTER_KEY = "mcp:calls:{day}"

SESSION_TTL = 300
CALLS_KEPT = 200
CALLS_TTL = 7 * 24 * 3600
COUNTER_TTL = 2 * 24 * 3600


@dataclass
class CallRecord:
    token_id: uuid.UUID
    token_name: str
    client: str
    tool: str
    ok: bool
    duration_ms: int
    detail: str | None = None


def _client() -> Any:
    from app.core.ratelimit import _client as redis_client  # noqa: PLC0415

    return redis_client()


async def touch(
    *,
    token_id: uuid.UUID,
    token_name: str,
    client: str,
    capabilities: list[str],
    tool: str | None,
) -> None:
    key = SESSION_KEY.format(token_id=token_id, client=_slug(client))
    now = utc_now()
    try:
        redis = _client()
        raw = await redis.get(key)
        existing = json.loads(raw) if raw else {}
        payload = {
            "token_id": str(token_id),
            "token_name": token_name,
            "client": client,
            "capabilities": capabilities,
            "first_seen": existing.get("first_seen", now.isoformat()),
            "last_seen": now.isoformat(),
            "calls": int(existing.get("calls", 0)) + (1 if tool else 0),
            "last_tool": tool or existing.get("last_tool"),
        }
        await redis.set(key, json.dumps(payload), ex=SESSION_TTL)
        await redis.sadd(SESSION_INDEX, key)
        await redis.expire(SESSION_INDEX, SESSION_TTL * 4)
    except Exception as exc:
        logger.debug("mcp session telemetry skipped", error=str(exc))


async def sessions() -> list[dict]:
    try:
        redis = _client()
        keys = sorted(await redis.smembers(SESSION_INDEX))
        if not keys:
            return []
        rows = await redis.mget(keys)
    except Exception as exc:
        logger.debug("mcp sessions unavailable", error=str(exc))
        return []

    live: list[dict] = []
    stale: list[str] = []
    for key, raw in zip(keys, rows, strict=False):
        if raw is None:
            stale.append(key)
            continue
        with contextlib.suppress(ValueError):
            live.append(json.loads(raw))
    if stale:
        with contextlib.suppress(Exception):
            await _client().srem(SESSION_INDEX, *stale)
    return sorted(live, key=lambda r: r.get("last_seen", ""), reverse=True)


async def drop(token_id: uuid.UUID, client: str | None = None) -> int:
    """Forget a session so the UI stops showing it. The token itself stays valid."""
    try:
        redis = _client()
        keys = [
            k
            for k in await redis.smembers(SESSION_INDEX)
            if k.startswith(SESSION_KEY.format(token_id=token_id, client=""))
            or (
                client
                and k == SESSION_KEY.format(token_id=token_id, client=_slug(client))
            )
        ]
        if not keys:
            return 0
        await redis.delete(*keys)
        await redis.srem(SESSION_INDEX, *keys)
    except Exception as exc:
        logger.debug("mcp session drop skipped", error=str(exc))
        return 0
    return len(keys)


async def record(call: CallRecord) -> None:
    now = utc_now()
    entry = {
        "at": now.isoformat(),
        "token_name": call.token_name,
        "client": call.client,
        "tool": call.tool,
        "ok": call.ok,
        "duration_ms": call.duration_ms,
        "detail": call.detail,
    }
    try:
        redis = _client()
        await redis.lpush(CALLS_KEY, json.dumps(entry))
        await redis.ltrim(CALLS_KEY, 0, CALLS_KEPT - 1)
        await redis.expire(CALLS_KEY, CALLS_TTL)
        counter = COUNTER_KEY.format(day=now.date().isoformat())
        await redis.incr(counter)
        await redis.expire(counter, COUNTER_TTL)
    except Exception as exc:
        logger.debug("mcp call telemetry skipped", error=str(exc))


async def recent(limit: int = 100) -> list[dict]:
    try:
        raw = await _client().lrange(CALLS_KEY, 0, max(0, limit - 1))
    except Exception as exc:
        logger.debug("mcp call trail unavailable", error=str(exc))
        return []
    entries: list[dict] = []
    for item in raw:
        with contextlib.suppress(ValueError):
            entries.append(json.loads(item))
    return entries


async def calls_today() -> int:
    key = COUNTER_KEY.format(day=utc_now().date().isoformat())
    try:
        value = await _client().get(key)
    except Exception:
        return 0
    return int(value or 0)


async def last_call_at() -> datetime | None:
    entries = await recent(1)
    if not entries:
        return None
    with contextlib.suppress(ValueError, TypeError):
        return datetime.fromisoformat(entries[0]["at"])
    return None


def _slug(value: str) -> str:
    keep = [c if c.isalnum() or c in "-_." else "-" for c in value.lower()]
    return "".join(keep)[:48] or "unknown"
