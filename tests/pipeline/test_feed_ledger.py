from __future__ import annotations

import pytest
from sqlalchemy import delete, select

from shared.definitions.threat_intel import FeedStatus
from shared.models.threat_intel import ThreatFeed
from shared.services import feed_ledger

pytestmark = pytest.mark.pipeline

PREFIX = "t_ledger_"


class MirrorError(RuntimeError):
    pass


async def _row(session, kind: str) -> ThreatFeed:
    session.expire_all()
    return (
        await session.execute(select(ThreatFeed).where(ThreatFeed.kind == kind))
    ).scalar_one()


@pytest.fixture
async def ledger(session):
    yield session
    await session.execute(delete(ThreatFeed).where(ThreatFeed.kind.like(f"{PREFIX}%")))
    await session.commit()


def _load(kind: str, rows: int, version: str):
    def run(sync):
        with feed_ledger.refreshing(sync, kind) as refresh:
            refresh.rows, refresh.version, refresh.size = rows, version, 2048

    return run


async def test_a_load_records_its_rows_and_version(ledger):
    kind = f"{PREFIX}ready"
    await ledger.run_sync(_load(kind, 12, "v1"))

    row = await _row(ledger, kind)
    assert row.status == FeedStatus.READY.value
    assert (row.rows, row.version, row.bytes) == (12, "v1", 2048)
    assert row.last_synced_at is not None
    assert row.error is None


async def test_the_syncing_mark_keeps_the_last_version(ledger):
    kind = f"{PREFIX}stamp"
    await ledger.run_sync(_load(kind, 12, "v1"))

    await ledger.run_sync(
        lambda sync: feed_ledger.mark(sync, kind, status=FeedStatus.SYNCING.value)
    )

    row = await _row(ledger, kind)
    assert row.status == FeedStatus.SYNCING.value
    assert (row.rows, row.version) == (12, "v1")


async def test_a_raising_load_is_recorded_failed_and_reraised(ledger):
    kind = f"{PREFIX}raise"
    await ledger.run_sync(_load(kind, 12, "v1"))

    def broken(sync):
        with feed_ledger.refreshing(sync, kind):
            msg = "mirror returned 503"
            raise MirrorError(msg)

    with pytest.raises(MirrorError):
        await ledger.run_sync(broken)

    row = await _row(ledger, kind)
    assert row.status == FeedStatus.FAILED.value
    assert row.error == "mirror returned 503"
    assert (row.rows, row.version) == (12, "v1")


async def test_a_load_that_reports_an_error_is_failed(ledger):
    kind = f"{PREFIX}partial"

    def partial(sync):
        with feed_ledger.refreshing(sync, kind) as refresh:
            refresh.rows = 3
            refresh.error = "ip_country_ranges: timed out"

    await ledger.run_sync(partial)

    row = await _row(ledger, kind)
    assert row.status == FeedStatus.FAILED.value
    assert row.error == "ip_country_ranges: timed out"
    assert row.last_synced_at is None
