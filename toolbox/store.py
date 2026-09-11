"""Run records, held in Redis with a TTL."""

from __future__ import annotations

import json
import uuid
from typing import Any

import redis as sync_redis

from shared.config import BaseAppSettings
from shared.definitions.toolbox import (
    RUN_TTL_SECONDS,
    RUNS_KEPT,
    RUNS_PER_MINUTE,
    RunStatus,
    ToolRunRead,
)
from shared.logging import get_logger
from shared.utils.datetime import utc_now

logger = get_logger(__name__)

RUN_KEY = "toolbox:run:{user_id}:{run_id}"
INDEX_KEY = "toolbox:runs:{user_id}"
RATE_KEY = "toolbox:rate:{user_id}"

_sync_client: Any = None


def _async_client() -> Any:
    from app.core.ratelimit import _client  # noqa: PLC0415

    return _client()


def _worker_client() -> Any:
    global _sync_client  # noqa: PLW0603
    if _sync_client is None:
        _sync_client = sync_redis.from_url(
            BaseAppSettings().redis_url, decode_responses=True
        )
    return _sync_client


def new_run(
    *,
    tool: str,
    title: str,
    label: str,
    payload: dict,
    status: str,
) -> ToolRunRead:
    return ToolRunRead(
        id=str(uuid.uuid4()),
        tool=tool,
        title=title,
        label=label,
        input=payload,
        status=status,
        queued_at=utc_now().isoformat(),
    )


def _dump(run: ToolRunRead) -> str:
    return run.model_dump_json()


def _load(raw: str | None) -> ToolRunRead | None:
    if not raw:
        return None
    try:
        return ToolRunRead.model_validate(json.loads(raw))
    except (ValueError, TypeError):
        return None


async def save(user_id: uuid.UUID, run: ToolRunRead) -> None:
    key = RUN_KEY.format(user_id=user_id, run_id=run.id)
    index = INDEX_KEY.format(user_id=user_id)
    try:
        redis = _async_client()
        pipe = redis.pipeline(transaction=False)
        pipe.set(key, _dump(run), ex=RUN_TTL_SECONDS)
        pipe.lrem(index, 0, run.id)
        pipe.lpush(index, run.id)
        pipe.ltrim(index, 0, RUNS_KEPT - 1)
        pipe.expire(index, RUN_TTL_SECONDS)
        await pipe.execute()
    except Exception as exc:
        logger.debug("toolbox run not stored", error=str(exc))


async def get(user_id: uuid.UUID, run_id: str) -> ToolRunRead | None:
    try:
        raw = await _async_client().get(RUN_KEY.format(user_id=user_id, run_id=run_id))
    except Exception as exc:
        logger.debug("toolbox run unavailable", error=str(exc))
        return None
    return _load(raw)


async def recent(user_id: uuid.UUID, limit: int = RUNS_KEPT) -> list[ToolRunRead]:
    index = INDEX_KEY.format(user_id=user_id)
    try:
        redis = _async_client()
        ids = await redis.lrange(index, 0, limit - 1)
        if not ids:
            return []
        rows = await redis.mget(
            [RUN_KEY.format(user_id=user_id, run_id=i) for i in ids]
        )
    except Exception as exc:
        logger.debug("toolbox history unavailable", error=str(exc))
        return []
    runs = [_load(raw) for raw in rows]
    return [r for r in runs if r is not None]


async def clear(user_id: uuid.UUID) -> int:
    index = INDEX_KEY.format(user_id=user_id)
    try:
        redis = _async_client()
        ids = await redis.lrange(index, 0, -1)
        keys = [RUN_KEY.format(user_id=user_id, run_id=i) for i in ids]
        if keys:
            await redis.delete(*keys)
        await redis.delete(index)
    except Exception as exc:
        logger.debug("toolbox history not cleared", error=str(exc))
        return 0
    return len(ids)


async def within_rate(user_id: uuid.UUID) -> bool:
    """Fail-open per-user throughput guard."""
    key = RATE_KEY.format(user_id=user_id)
    try:
        redis = _async_client()
        pipe = redis.pipeline(transaction=True)
        pipe.incr(key)
        pipe.expire(key, 60, nx=True)
        count, _ = await pipe.execute()
    except Exception as exc:
        logger.debug("toolbox rate guard unavailable", error=str(exc))
        return True
    return int(count) <= RUNS_PER_MINUTE


def get_sync(user_id: str, run_id: str) -> ToolRunRead | None:
    try:
        raw = _worker_client().get(RUN_KEY.format(user_id=user_id, run_id=run_id))
    except Exception as exc:
        logger.debug("toolbox run unavailable", error=str(exc))
        return None
    return _load(raw)


def save_sync(user_id: str, run: ToolRunRead) -> None:
    key = RUN_KEY.format(user_id=user_id, run_id=run.id)
    try:
        _worker_client().set(key, _dump(run), ex=RUN_TTL_SECONDS, xx=True)
    except Exception as exc:
        logger.debug("toolbox run not stored", error=str(exc))


def mark_running(user_id: str, run_id: str) -> ToolRunRead | None:
    run = get_sync(user_id, run_id)
    if run is None:
        return None
    run.status = RunStatus.RUNNING.value
    run.started_at = utc_now().isoformat()
    save_sync(user_id, run)
    return run
