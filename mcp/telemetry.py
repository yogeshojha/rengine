"""Live sessions and the recent-call trail."""

from __future__ import annotations

import contextlib
import json
import uuid
from collections.abc import Collection
from dataclasses import dataclass

from shared.logging import get_logger
from shared.redis import async_client
from shared.utils.datetime import utc_now
from shared.utils.text import strip_control

logger = get_logger(__name__)

SESSION_KEY = "mcp:session:{token_id}:{client}"
SESSION_INDEX = "mcp:sessions"
CALLS_KEY = "mcp:calls"

SESSION_TTL = 300
CALLS_KEPT = 200
CALLS_TTL = 7 * 24 * 3600
ARGS_MAX = 200
SUMMARY_MAX = 240
TOOL_NAME_MAX = 64
LIST_SHOWN = 5
_SECRET_NAMES = ("token", "secret", "password", "header", "cookie", "auth", "key")


@dataclass
class CallRecord:
    token_id: uuid.UUID
    token_name: str
    client: str
    tool: str
    ok: bool
    duration_ms: int
    detail: str | None = None
    command: str | None = None
    capability: str | None = None
    args: str | None = None
    summary: str | None = None
    pivot: str | None = None
    refused: bool = False


def phrase_args(values: dict | None) -> str | None:
    """One line of the arguments a person can read, secrets left out."""
    parts: list[str] = []
    for name, value in (values or {}).items():
        if value in (None, "", [], {}) or isinstance(value, dict):
            continue
        if any(word in name.lower() for word in _SECRET_NAMES):
            continue
        text = str(value)
        if isinstance(value, list | tuple):
            shown = ", ".join(str(v) for v in value[:LIST_SHOWN])
            extra = len(value) - LIST_SHOWN
            text = f"{shown} +{extra}" if extra > 0 else shown
        parts.append(f"{name}={text}")
    text = strip_control(" ".join(parts))[:ARGS_MAX]
    return text or None


def clip(value: str | None, limit: int = SUMMARY_MAX) -> str | None:
    return strip_control(value)[:limit] if value else None


async def touch(*, token_id: uuid.UUID, client: str) -> None:
    key = SESSION_KEY.format(token_id=token_id, client=_slug(client))
    payload = {
        "token_id": str(token_id),
        "client": client,
        "last_seen": utc_now().isoformat(),
    }
    try:
        redis = async_client()
        await redis.set(key, json.dumps(payload), ex=SESSION_TTL)
        await redis.sadd(SESSION_INDEX, key)
        await redis.expire(SESSION_INDEX, SESSION_TTL * 4)
    except Exception as exc:
        logger.debug("mcp session telemetry skipped", error=str(exc))


async def sessions() -> list[dict]:
    try:
        redis = async_client()
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
            await async_client().srem(SESSION_INDEX, *stale)
    return sorted(live, key=lambda r: r.get("last_seen", ""), reverse=True)


async def drop(token_id: uuid.UUID) -> int:
    """Forget a session."""
    prefix = SESSION_KEY.format(token_id=token_id, client="")
    try:
        redis = async_client()
        keys = [k for k in await redis.smembers(SESSION_INDEX) if k.startswith(prefix)]
        if not keys:
            return 0
        await redis.delete(*keys)
        await redis.srem(SESSION_INDEX, *keys)
    except Exception as exc:
        logger.debug("mcp session drop skipped", error=str(exc))
        return 0
    return len(keys)


async def record(call: CallRecord) -> None:
    entry = {
        "at": utc_now().isoformat(),
        "token_id": str(call.token_id),
        "token_name": call.token_name,
        "client": call.client,
        "tool": call.tool,
        "ok": call.ok,
        "duration_ms": call.duration_ms,
        "detail": call.detail,
        "command": call.command,
        "capability": call.capability,
        "args": call.args,
        "summary": call.summary,
        "pivot": call.pivot,
        "refused": call.refused,
    }
    try:
        redis = async_client()
        await redis.lpush(CALLS_KEY, json.dumps(entry))
        await redis.ltrim(CALLS_KEY, 0, CALLS_KEPT - 1)
        await redis.expire(CALLS_KEY, CALLS_TTL)
    except Exception as exc:
        logger.debug("mcp call telemetry skipped", error=str(exc))


async def recent(
    limit: int = 100,
    *,
    client: str | None = None,
    without: Collection[str] = (),
) -> list[dict]:
    """The newest calls a client made, filtered before the cut."""
    try:
        raw = await async_client().lrange(CALLS_KEY, 0, CALLS_KEPT - 1)
    except Exception as exc:
        logger.debug("mcp call trail unavailable", error=str(exc))
        return []
    entries: list[dict] = []
    for item in raw:
        with contextlib.suppress(ValueError):
            entry = json.loads(item)
            if _wanted(entry.get("client"), client, without):
                entries.append(entry)
        if len(entries) >= limit:
            break
    return entries


def _wanted(value: str | None, client: str | None, without: Collection[str]) -> bool:
    if client is not None:
        return value == client
    return value not in without


def _slug(value: str) -> str:
    keep = [c if c.isalnum() or c in "-_." else "-" for c in value.lower()]
    return "".join(keep)[:48] or "unknown"
