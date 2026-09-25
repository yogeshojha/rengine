from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import delete, select, text

from app.services import scan_deltas as stored
from app.services.scan import ScanService
from shared.definitions.surface import SurfaceDimension
from shared.models.scan import Scan
from shared.models.scan_delta import ScanDelta, ScanRevision
from shared.models.subdomain import Subdomain
from shared.services import scan_deltas

pytestmark = pytest.mark.api

WEB = SurfaceDimension.WEB_ASSETS.value


async def _three_runs(estate, now):
    await estate.scan("example.com", "one", at=now - timedelta(days=2))
    await estate.hosts(
        "one", ["a.example.com", "b.example.com"], at=now - timedelta(days=2)
    )
    await estate.scan("example.com", "two", at=now - timedelta(days=1))
    await estate.hosts(
        "two", ["a.example.com", "c.example.com"], at=now - timedelta(days=1)
    )
    await estate.scan("example.com", "three", at=now)
    await estate.hosts(
        "three", ["a.example.com", "c.example.com", "d.example.com"], at=now
    )
    await estate.session.commit()
    return [estate.scans[name] for name in ("one", "two", "three")]


async def _stored_rows(session):
    return (await session.execute(select(ScanDelta))).scalars().all()


async def test_first_seen_counts_each_name_once_per_target(durable_estate, now):
    one, two, three = await _three_runs(durable_estate, now)

    counts = await stored.first_seen(durable_estate.session, WEB, [one, two, three])

    assert counts == {one: 2, two: 1, three: 1}


async def test_a_stored_count_is_read_back_without_recounting(durable_estate, now):
    one, two, three = await _three_runs(durable_estate, now)
    await stored.first_seen(durable_estate.session, WEB, [one, two, three])

    _, fill, _ = await durable_estate.session.run_sync(
        lambda s: scan_deltas.first_seen(s, WEB, [one, two, three])
    )

    assert not fill, "every count was valid, so nothing was computed"
    assert len(await _stored_rows(durable_estate.session)) == 3


async def test_deleting_an_earlier_row_recounts_the_later_runs(durable_estate, now):
    one, two, three = await _three_runs(durable_estate, now)
    await stored.first_seen(durable_estate.session, WEB, [one, two, three])

    await durable_estate.session.execute(
        delete(Subdomain).where(
            Subdomain.scan_id == one, Subdomain.name == "a.example.com"
        )
    )
    await durable_estate.session.commit()
    counts = await stored.first_seen(durable_estate.session, WEB, [one, two, three])

    assert counts == {one: 1, two: 2, three: 1}, "run two now first saw a.example.com"


async def test_a_late_row_in_a_settled_run_moves_only_that_run(durable_estate, now):
    one, two, three = await _three_runs(durable_estate, now)
    await stored.first_seen(durable_estate.session, WEB, [one, two, three])
    before = {
        r.scan_id: r.history_rev
        for r in (await durable_estate.session.execute(select(ScanRevision)))
        .scalars()
        .all()
    }

    await durable_estate.hosts("two", ["e.example.com"], at=now + timedelta(minutes=5))
    await durable_estate.session.commit()
    after = {
        r.scan_id: r.history_rev
        for r in (await durable_estate.session.execute(select(ScanRevision)))
        .scalars()
        .all()
    }
    counts = await stored.first_seen(durable_estate.session, WEB, [one, two, three])

    assert after[two] > before[two]
    assert after.get(three) == before.get(three), "e.example.com landed after run three"
    assert counts == {one: 2, two: 2, three: 1}


async def test_retired_counts_what_the_previous_run_held(durable_estate, now):
    one, two, three = await _three_runs(durable_estate, now)

    counts = await stored.retired(
        durable_estate.session, WEB, [(two, one), (three, two)]
    )

    assert counts == {(two, one): 1, (three, two): 0}


async def test_retired_recounts_when_the_previous_run_changes(durable_estate, now):
    _, two, three = await _three_runs(durable_estate, now)
    await stored.retired(durable_estate.session, WEB, [(three, two)])

    await durable_estate.hosts("two", ["z.example.com"], at=now + timedelta(minutes=5))
    await durable_estate.session.commit()
    counts = await stored.retired(durable_estate.session, WEB, [(three, two)])

    assert counts == {(three, two): 1}, "z.example.com is missing from run three"


async def test_an_older_count_never_replaces_a_newer_one(durable_estate, now):
    one, _, _ = await _three_runs(durable_estate, now)
    await stored.first_seen(durable_estate.session, WEB, [one])
    await durable_estate.session.execute(
        text(
            "UPDATE scan_deltas SET history_rev = history_rev + 5, first_seen = 99 "
            "WHERE scan_id = :sid"
        ).bindparams(sid=one)
    )
    await durable_estate.session.commit()

    await durable_estate.session.run_sync(
        lambda s: scan_deltas.store(
            s,
            scan_deltas.Fill(
                [
                    {
                        "scan_id": one,
                        "dimension": WEB,
                        "history_rev": 0,
                        "first_seen": 1,
                        "rows": 1,
                        "first_at": now,
                    }
                ],
                [],
            ),
        )
    )
    await durable_estate.session.commit()
    row = (
        await durable_estate.session.execute(
            select(ScanDelta.first_seen).where(ScanDelta.scan_id == one)
        )
    ).scalar_one()

    assert row == 99


async def test_a_live_run_answers_from_its_last_count(durable_estate, now):
    _, _, three = await _three_runs(durable_estate, now)
    await stored.first_seen(durable_estate.session, WEB, [three])
    await durable_estate.hosts(
        "three", ["f.example.com"], at=now + timedelta(minutes=1)
    )
    await durable_estate.session.commit()

    counts, fill, stale = await durable_estate.session.run_sync(
        lambda s: scan_deltas.first_seen(s, WEB, [three], reuse=frozenset({three}))
    )

    assert counts == {three: 1}, "the stored count stands until the refresh lands"
    assert stale == {three}
    assert not fill


async def test_deleting_a_run_recounts_the_runs_after_it(durable_estate, now):
    one, two, three = await _three_runs(durable_estate, now)
    await stored.first_seen(durable_estate.session, WEB, [one, two, three])

    await durable_estate.session.execute(
        text("DELETE FROM scans WHERE id = :sid").bindparams(sid=one)
    )
    await durable_estate.session.commit()
    counts = await stored.first_seen(durable_estate.session, WEB, [two, three])

    assert counts == {two: 2, three: 1}


async def test_row_counts_skip_runs_without_rows(durable_estate, now):
    one, _, three = await _three_runs(durable_estate, now)
    await durable_estate.scan("example.com", "empty", at=now + timedelta(hours=1))
    await durable_estate.session.commit()
    empty = durable_estate.scans["empty"]

    counts = await stored.row_counts(durable_estate.session, WEB, [one, three, empty])

    assert set(counts) == {one, three}
    assert counts[three][0] == 3


async def test_the_scan_list_reads_stored_new_and_gone(durable_estate, now):
    one, two, three = await _three_runs(durable_estate, now)
    service = ScanService(durable_estate.session)

    new = await service.new_subdomain_counts([one, two, three])
    gone = await service.gone_subdomain_counts(
        [two, three], [durable_estate.targets["example.com"]]
    )

    assert new == {one: 2, two: 1, three: 1}
    assert gone == {two: 1, three: 0}


async def test_the_backfill_finds_settled_runs_until_they_are_warm(durable_estate, now):
    one, two, three = await _three_runs(durable_estate, now)
    await durable_estate.scan(
        "example.com", "live", at=now + timedelta(hours=1), status="running"
    )
    await durable_estate.session.commit()

    def pending(session):
        return set(scan_deltas.pending_scans(session, limit=50))

    before = await durable_estate.session.run_sync(pending)
    for sid in (one, two, three):
        await durable_estate.session.run_sync(
            lambda s, sid=sid: scan_deltas.warm(s, s.get(Scan, sid))
        )
    after = await durable_estate.session.run_sync(pending)

    assert before == {one, two, three}, "a live run is never backfilled"
    assert after == set()
    retired = await stored.retired(durable_estate.session, WEB, [(three, two)])
    assert retired == {(three, two): 0}
