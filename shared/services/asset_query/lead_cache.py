"""Lead counts for a finished scan never change, so they are computed once."""

from __future__ import annotations

import hashlib
from collections.abc import Awaitable, Callable
from uuid import UUID

import redis.asyncio as aioredis
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

# A finished scan's own rows never change, but the counts drawn from them do: a
# reviewer suppressing a finding moves every vulnerability lead, the nightly EPSS and
# KEV load moves is:kev, and an interest pass moves is:exposed. Rather than plumb an
# invalidation into each of those and hope none is ever missed, the entry is short
# lived: it serves the burst — tab switches, facet changes, a second table on the same
# page — and any count is at most this stale.
TTL_SECONDS = 60

_client: aioredis.Redis | None = None


def _redis() -> aioredis.Redis:
    global _client  # noqa: PLW0603
    if _client is None:
        _client = aioredis.from_url(BaseAppSettings().redis_url, decode_responses=True)
    return _client


# paging and sorting do not change a count, and the lead set deliberately ignores
# the search box: what is cached is the unfiltered-by-text view the page opens with
_IGNORED = {"q", "page", "size", "limit", "offset", "sort", "direction", "order"}


def facets_of(model) -> str:
    return model.model_dump_json(exclude=_IGNORED)


def fingerprint(*parts: object) -> str:
    raw = "\x1f".join(str(part) for part in parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


async def _settled(session: AsyncSession, scans: tuple[UUID, ...]) -> bool:
    """Whether every scan in the scope has finished writing.

    A live scan's counts change under the reader, and the count is a promise: it must
    equal the rows its link opens. So only a settled scope is ever cached.
    """
    if not scans:
        return False
    statuses = await session.scalars(select(Scan.status).where(Scan.id.in_(scans)))
    rows = list(statuses)
    return len(rows) == len(set(scans)) and all(
        status in SCAN_TERMINAL_STATUSES for status in rows
    )


async def leads(
    session: AsyncSession,
    *,
    dimension: str,
    scans: tuple[UUID, ...],
    facets: str,
    build: Callable[[], Awaitable[QueryLeads]],
) -> QueryLeads:
    """Serve the lead set from redis when the scope has settled. Fail-open throughout:
    a redis outage costs the cache, never the answer."""
    if not await _settled(session, scans):
        return await build()

    key = f"leads:{VERSION}:{dimension}:{fingerprint(sorted(map(str, scans)), facets)}"
    try:
        hit = await _redis().get(key)
        if hit:
            return QueryLeads.model_validate_json(hit)
    except Exception:
        logger.debug("lead cache unavailable on read", exc_info=True)

    computed = await build()
    if not computed.computed:
        return computed
    try:
        await _redis().set(key, computed.model_dump_json(), ex=TTL_SECONDS)
    except Exception:
        logger.debug("lead cache unavailable on write", exc_info=True)
    return computed
