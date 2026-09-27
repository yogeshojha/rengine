"""The last refresh of each downloaded dataset."""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from shared.definitions.threat_intel import FeedStatus
from shared.logging import get_logger
from shared.models.threat_intel import ThreatFeed
from shared.utils.datetime import utc_now
from shared.utils.text import strip_nul

logger = get_logger(__name__)

MAX_ERROR = 500


def mark(session: Session, kind: str, *, status: str, **fields: object) -> None:
    """Upsert the ledger row, touching only the fields given."""
    now = utc_now()
    changed = {"status": status, "last_attempt_at": now, "updated_at": now, **fields}
    first = {"kind": kind, "rows": 0, "bytes": 0, "duration_ms": 0, **changed}
    session.execute(
        pg_insert(ThreatFeed)
        .values(**first)
        .on_conflict_do_update(index_elements=[ThreatFeed.kind], set_=changed)
    )


@dataclass
class Refresh:
    rows: int = 0
    version: str | None = None
    size: int = 0
    error: str | None = None


def _elapsed(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


def _failed(session: Session, kind: str, started: float, error: str) -> None:
    mark(
        session,
        kind,
        status=FeedStatus.FAILED.value,
        duration_ms=_elapsed(started),
        error=strip_nul(error)[:MAX_ERROR],
    )
    session.commit()


@contextmanager
def refreshing(session: Session, kind: str) -> Iterator[Refresh]:
    """Record one load: syncing, then ready or failed."""
    started = time.monotonic()
    mark(session, kind, status=FeedStatus.SYNCING.value, error=None)
    session.commit()
    refresh = Refresh()
    try:
        yield refresh
    except Exception as exc:
        session.rollback()
        try:
            _failed(session, kind, started, str(exc) or type(exc).__name__)
        except Exception:
            session.rollback()
            logger.warning("feed ledger write failed", feed=kind, exc_info=True)
        raise
    if refresh.error:
        _failed(session, kind, started, refresh.error)
        return
    mark(
        session,
        kind,
        status=FeedStatus.READY.value,
        rows=refresh.rows,
        version=refresh.version,
        bytes=refresh.size,
        duration_ms=_elapsed(started),
        error=None,
        last_synced_at=utc_now(),
    )
    session.commit()


def dataset_status(
    *,
    loading: bool,
    recorded: str | None,
    synced_at: datetime | None,
    present: bool,
    stale_after_hours: int | None,
    now: datetime,
) -> str:
    if loading:
        return FeedStatus.SYNCING.value
    if recorded == FeedStatus.FAILED.value:
        return FeedStatus.FAILED.value
    if not present:
        return FeedStatus.EMPTY.value
    if (
        stale_after_hours
        and synced_at
        and (now - synced_at).total_seconds() > stale_after_hours * 3600
    ):
        return FeedStatus.STALE.value
    return FeedStatus.READY.value
