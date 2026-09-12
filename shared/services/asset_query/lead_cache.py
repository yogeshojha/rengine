"""Aggregates of a settled scope, cached by target revision."""

from __future__ import annotations

import hashlib
from collections.abc import Awaitable, Callable, Iterable
from uuid import UUID

import redis
import redis.asyncio as aioredis
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config import BaseAppSettings
from shared.enums.scan import SCAN_TERMINAL_STATUSES
from shared.logging import get_logger
from shared.models.asset_query import QueryLeads
from shared.models.scan import Scan

logger = get_logger(__name__)

# bumped when the shape of a cached entry changes
VERSION = "1"

TTL_SECONDS = 6 * 3600
SEARCH_TTL_SECONDS = 600
_GLOBAL_KEY = "rev:global"

_client: aioredis.Redis | None = None


def _redis() -> aioredis.Redis:
    global _client  # noqa: PLW0603
    if _client is None:
        _client = aioredis.from_url(BaseAppSettings().redis_url, decode_responses=True)
    return _client


_IGNORED = {"q", "page", "size", "limit", "offset", "sort", "direction", "order"}


def facets_of(model) -> str:
    return model.model_dump_json(exclude=_IGNORED)


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
    values = await _redis().mget([_GLOBAL_KEY, *(_revision_key(t) for t in targets)])
    return [value or "0" for value in values]


async def bump(targets: Iterable[UUID]) -> None:
    """Retire every cached aggregate of the targets."""
    try:
        async with _redis().pipeline() as pipe:
            for target_id in set(targets):
                pipe.incr(_revision_key(target_id))
            await pipe.execute()
    except Exception:
        logger.debug("aggregate cache revision bump failed", exc_info=True)


async def bump_global() -> None:
    """Retire every cached aggregate."""
    try:
        await _redis().incr(_GLOBAL_KEY)
    except Exception:
        logger.debug("aggregate cache revision bump failed", exc_info=True)


def bump_sync(targets: Iterable[UUID], redis_url: str | None = None) -> None:
    try:
        url = redis_url or BaseAppSettings().redis_url
        with redis.from_url(url) as client, client.pipeline() as pipe:
            for target_id in set(targets):
                pipe.incr(_revision_key(target_id))
            pipe.execute()
    except Exception:
        logger.debug("aggregate cache revision bump failed", exc_info=True)


def bump_global_sync(redis_url: str | None = None) -> None:
    try:
        with redis.from_url(redis_url or BaseAppSettings().redis_url) as client:
            client.incr(_GLOBAL_KEY)
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
) -> T:
    """One aggregate of a settled scope."""
    settled, targets = await _settled(session, scans)
    if not settled:
        return await build()

    try:
        revisions = await _revisions(targets)
    except Exception:
        logger.debug("aggregate cache unavailable on read", name=name, exc_info=True)
        return await build()
    key = (
        f"{name}:{VERSION}:"
        f"{fingerprint(sorted(map(str, scans)), facets, ','.join(revisions))}"
    )
    try:
        hit = await _redis().get(key)
        if hit:
            return model.model_validate_json(hit)
    except Exception:
        logger.debug("aggregate cache unavailable on read", name=name, exc_info=True)

    computed = await build()
    if not keep(computed):
        return computed
    try:
        await _redis().set(key, computed.model_dump_json(), ex=ttl)
    except Exception:
        logger.debug("aggregate cache unavailable on write", name=name, exc_info=True)
    return computed


async def leads(
    session: AsyncSession,
    *,
    dimension: str,
    scans: tuple[UUID, ...],
    facets: str,
    build: Callable[[], Awaitable[QueryLeads]],
) -> QueryLeads:
    """The cached lead set for a settled scope."""
    return await cached(
        session,
        name=f"leads:{dimension}",
        scans=scans,
        facets=facets,
        model=QueryLeads,
        build=build,
        keep=lambda computed: computed.computed,
    )
