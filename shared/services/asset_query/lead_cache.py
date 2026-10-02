"""Aggregates of a settled scope, cached by target revision."""

from __future__ import annotations

import asyncio
import hashlib
import time
from collections.abc import Awaitable, Callable, Iterable
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.enums.scan import SCAN_TERMINAL_STATUSES
from shared.logging import get_logger
from shared.models.asset_query import QueryLeads
from shared.models.scan import Scan
from shared.redis import async_client, sync_client

logger = get_logger(__name__)

# bumped when the shape of a cached entry changes
VERSION = "5"

TTL_SECONDS = 6 * 3600
SEARCH_TTL_SECONDS = 600
LIVE_TTL_SECONDS = 20
STALE_TTL_SECONDS = 15 * 60
BUILD_LOCK_SECONDS = 120
BUILD_WAIT_SECONDS = 30
BUILD_POLL_SECONDS = 0.2
_RELEASE = (
    "if redis.call('get', KEYS[1]) == ARGV[1] then "
    "return redis.call('del', KEYS[1]) end return 0"
)
_GLOBAL_KEY = "rev:global"

_PAGING = {"page", "size", "limit", "offset", "sort", "direction", "order"}
_IGNORED = {"q", *_PAGING}


def facets_of(model) -> str:
    return model.model_dump_json(exclude=_IGNORED)


def filter_of(model) -> str:
    return model.model_dump_json(exclude=_PAGING)


def fingerprint(*parts: object) -> str:
    raw = "\x1f".join(str(part) for part in parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


async def _settled(
    session: AsyncSession, scans: tuple[UUID, ...]
) -> tuple[bool, list[UUID]]:
    """Whether every scan in the scope has finished writing, and the targets they cover."""
    if not scans:
        return False, []
    rows = (
        await session.execute(
            select(Scan.status, Scan.target_id).where(Scan.id.in_(scans))
        )
    ).all()
    settled = len(rows) == len(set(scans)) and all(
        status in SCAN_TERMINAL_STATUSES for status, _ in rows
    )
    return settled, sorted({target_id for _, target_id in rows}, key=str)


def _revision_key(target_id: UUID | str) -> str:
    return f"rev:target:{target_id}"


async def _revisions(targets: list[UUID]) -> list[str]:
    values = await async_client().mget(
        [_GLOBAL_KEY, *(_revision_key(t) for t in targets)]
    )
    return [value or "0" for value in values]


async def bump(targets: Iterable[UUID]) -> None:
    """Retire every cached aggregate of the targets."""
    try:
        async with async_client().pipeline() as pipe:
            for target_id in set(targets):
                pipe.incr(_revision_key(target_id))
            await pipe.execute()
    except Exception:
        logger.debug("aggregate cache revision bump failed", exc_info=True)


def bump_sync(targets: Iterable[UUID]) -> None:
    try:
        with sync_client().pipeline() as pipe:
            for target_id in set(targets):
                pipe.incr(_revision_key(target_id))
            pipe.execute()
    except Exception:
        logger.debug("aggregate cache revision bump failed", exc_info=True)


async def cached[T: BaseModel](
    session: AsyncSession,
    *,
    name: str,
    scans: tuple[UUID, ...],
    facets: str,
    model: type[T],
    build: Callable[[], Awaitable[T]],
    keep: Callable[[T], bool] = lambda _: True,
    ttl: int = TTL_SECONDS,
    live_ttl: int | None = LIVE_TTL_SECONDS,
) -> T:
    """One aggregate of a scope; a live scope is held for `live_ttl`, or not at all."""
    settled, targets = await _settled(session, scans)
    if not scans or (not settled and live_ttl is None):
        return await build()

    try:
        revisions = await _revisions(targets)
    except Exception:
        logger.debug("aggregate cache unavailable on read", name=name, exc_info=True)
        return await build()
    digest = fingerprint(sorted(map(str, scans)), facets, ",".join(revisions))
    key = f"{name}:{VERSION}:{digest}" if settled else f"live:{name}:{VERSION}:{digest}"
    stale_key = None if settled else f"{key}:stale"

    hit = await _read(key, model, name)
    if hit is not None:
        return hit
    token = await _claim(key, name)
    if token is None:
        fallback = await _read(stale_key, model, name) if stale_key else None
        if fallback is None:
            fallback = await _await_build(key, model, name)
        if fallback is not None:
            return fallback
    try:
        computed = await build()
        if getattr(computed, "error", None) is None and keep(computed):
            await _write(key, computed, ttl if settled else live_ttl, name)
            if stale_key:
                await _write(stale_key, computed, STALE_TTL_SECONDS, name)
        return computed
    finally:
        if token is not None:
            await _release(key, token)


async def _read[T: BaseModel](key: str, model: type[T], name: str) -> T | None:
    try:
        hit = await async_client().get(key)
    except Exception:
        logger.debug("aggregate cache unavailable on read", name=name, exc_info=True)
        return None
    return model.model_validate_json(hit) if hit else None


async def _write(key: str, value: BaseModel, ttl: int, name: str) -> None:
    try:
        await async_client().set(key, value.model_dump_json(), ex=ttl)
    except Exception:
        logger.debug("aggregate cache unavailable on write", name=name, exc_info=True)


async def _claim(key: str, name: str) -> str | None:
    """Whether this request builds the value; None when another one already is."""
    token = uuid4().hex
    try:
        claimed = await async_client().set(
            f"building:{key}", token, nx=True, ex=BUILD_LOCK_SECONDS
        )
    except Exception:
        logger.debug("aggregate cache unavailable on claim", name=name, exc_info=True)
        return token
    return token if claimed else None


async def _release(key: str, token: str) -> None:
    try:
        await async_client().eval(_RELEASE, 1, f"building:{key}", token)
    except Exception:
        logger.debug("aggregate cache build lock not released", exc_info=True)


async def _await_build[T: BaseModel](key: str, model: type[T], name: str) -> T | None:
    """The value another request is building, once it lands."""
    deadline = time.monotonic() + BUILD_WAIT_SECONDS
    while time.monotonic() < deadline:
        await asyncio.sleep(BUILD_POLL_SECONDS)
        hit = await _read(key, model, name)
        if hit is not None:
            return hit
        try:
            if not await async_client().exists(f"building:{key}"):
                return None
        except Exception:
            return None
    return None


async def leads(
    session: AsyncSession,
    *,
    dimension: str,
    scans: tuple[UUID, ...],
    facets: str,
    build: Callable[[], Awaitable[QueryLeads]],
) -> QueryLeads:
    """The cached lead set for a scope."""
    return await cached(
        session,
        name=f"leads:{dimension}",
        scans=scans,
        facets=facets,
        model=QueryLeads,
        build=build,
        keep=lambda computed: computed.computed,
    )
