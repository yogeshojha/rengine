"""Stored first-seen and retired counts, read through from the api."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from shared.logging import get_logger
from shared.redis import async_client
from shared.services import scan_deltas
from shared.services.celery_dispatch import dispatch_scan_deltas_refresh

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import datetime
    from uuid import UUID


logger = get_logger(__name__)

REFRESH_DEBOUNCE_SECONDS = 30


async def first_seen(
    session: AsyncSession,
    dimension: str,
    scan_ids: Iterable[UUID],
    live: Iterable[UUID] = (),
) -> dict[UUID, int]:
    """Per scan, the keys it was the first to report; a live run answers from its last count."""
    ids = list(scan_ids)
    reuse = frozenset(live)
    counts, fill, stale = await session.run_sync(
        lambda sync: scan_deltas.first_seen(sync, dimension, ids, reuse=reuse)
    )
    await _store(session, fill)
    await _refresh(stale)
    return counts


async def row_counts(
    session: AsyncSession,
    dimension: str,
    scan_ids: Iterable[UUID],
    live: Iterable[UUID] = (),
) -> dict[UUID, tuple[int, datetime | None]]:
    """Per scan holding rows, how many and when the first landed; a live run is counted now."""
    ids = list(scan_ids)
    counting = frozenset(live)
    counts, fill = await session.run_sync(
        lambda sync: scan_deltas.row_counts(sync, dimension, ids, live=counting)
    )
    await _store(session, fill)
    return counts


async def retired(
    session: AsyncSession,
    dimension: str,
    pairs: Iterable[scan_deltas.Pair],
) -> dict[scan_deltas.Pair, int]:
    """Per (scan, previous scan), keys the previous one held that the scan lacks."""
    wanted = list(pairs)
    counts, fill = await session.run_sync(
        lambda sync: scan_deltas.retired(sync, dimension, wanted)
    )
    await _store(session, fill)
    return counts


async def _store(session: AsyncSession, fill: scan_deltas.Fill) -> None:
    """Write on a connection of its own."""
    if not fill:
        return
    try:
        async with AsyncSession(session.bind, expire_on_commit=False) as writer:
            await writer.run_sync(lambda sync: scan_deltas.store(sync, fill))
            await writer.commit()
    except Exception:
        logger.warning("scan deltas not stored", exc_info=True)


async def _refresh(scan_ids: set[UUID]) -> None:
    for scan_id in scan_ids:
        try:
            queued = await async_client().set(
                f"scan_deltas:refresh:{scan_id}",
                "1",
                nx=True,
                ex=REFRESH_DEBOUNCE_SECONDS,
            )
        except Exception:
            logger.debug("scan deltas debounce unavailable", exc_info=True)
            queued = True
        if queued:
            await asyncio.to_thread(dispatch_scan_deltas_refresh, str(scan_id))
