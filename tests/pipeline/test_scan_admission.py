from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from app.services.scan import ScanService
from shared.definitions.watch import WATCH_HOST_KEY
from shared.models.scan import Scan
from shared.services import scan_admission

pytestmark = pytest.mark.pipeline


async def _busy(estate) -> int:
    return (
        await estate.session.scalar(
            select(func.count()).select_from(Scan).where(scan_admission.running())
        )
        or 0
    )


@pytest.fixture
def limit(monkeypatch):
    def set_limit(value: int) -> None:
        monkeypatch.setattr(scan_admission, "configured", lambda _session: value)

    return set_limit


async def _scan(estate, name, now, minutes, status="pending", config=None):
    return await estate.scan(
        "example.com",
        name,
        at=now + timedelta(minutes=minutes),
        status=status,
        config=config,
    )


async def _admits(estate, scan_id) -> bool:
    def run(sync_session):
        return scan_admission.admits(sync_session, sync_session.get(Scan, scan_id))

    return await estate.session.run_sync(run)


async def test_the_oldest_pending_scan_takes_the_free_slot(estate, now, limit):
    older = await _scan(estate, "older", now, 1)
    newer = await _scan(estate, "newer", now, 2)
    limit(await _busy(estate) + 1)

    assert await _admits(estate, older)
    assert not await _admits(estate, newer)


async def test_a_running_scan_holds_its_slot(estate, now, limit):
    await _scan(estate, "live", now, 0, status="running")
    waiting = await _scan(estate, "waiting", now, 1)
    limit(await _busy(estate))

    assert not await _admits(estate, waiting)


async def test_a_paused_scan_frees_its_slot(estate, now, limit):
    await _scan(estate, "paused", now, 0, status="paused")
    waiting = await _scan(estate, "waiting", now, 1)
    limit(await _busy(estate) + 1)

    assert await _admits(estate, waiting)


async def test_a_queued_scan_cannot_be_paused(estate, now):
    held = await _scan(estate, "held", now, 1)

    with pytest.raises(HTTPException) as refused:
        await ScanService(estate.session).pause(held, estate.project_id)
    assert refused.value.status_code == 409


async def test_a_watch_probe_never_waits(estate, now, limit):
    await _scan(estate, "live", now, 0, status="running")
    await _scan(estate, "older", now, 1)
    probe = await _scan(
        estate, "probe", now, 2, config={WATCH_HOST_KEY: "a.example.com"}
    )
    limit(await _busy(estate))

    assert await _admits(estate, probe)


async def test_admissible_fills_the_free_slots_in_launch_order(estate, now, limit):
    first = await _scan(estate, "first", now, 1)
    second = await _scan(estate, "second", now, 2)
    await _scan(estate, "third", now, 3)
    probe = await _scan(
        estate, "probe", now, 4, config={WATCH_HOST_KEY: "a.example.com"}
    )
    ours = {estate.scans[n] for n in ("first", "second", "third", "probe")}
    limit(await _busy(estate) + 2)

    def run(sync_session):
        return [s.id for s in scan_admission.admissible(sync_session)]

    picked = [i for i in await estate.session.run_sync(run) if i in ours]
    assert picked == [probe, first, second]


async def test_a_full_instance_admits_only_probes(estate, now, limit):
    await _scan(estate, "live", now, 0, status="running")
    await _scan(estate, "waiting", now, 1)
    probe = await _scan(
        estate, "probe", now, 2, config={WATCH_HOST_KEY: "a.example.com"}
    )
    ours = {estate.scans["waiting"], probe}
    limit(await _busy(estate))

    def run(sync_session):
        return [s.id for s in scan_admission.admissible(sync_session)]

    assert [i for i in await estate.session.run_sync(run) if i in ours] == [probe]


async def test_positions_count_waiting_scans_in_launch_order(estate, now):
    first = await _scan(estate, "first", now, 1)
    second = await _scan(estate, "second", now, 2)
    await _scan(estate, "probe", now, 3, config={WATCH_HOST_KEY: "a.example.com"})

    rows = dict(
        (
            await estate.session.execute(
                scan_admission.positions_query([first, second])
            )
        ).all()
    )
    assert rows[second] == rows[first] + 1


@pytest.mark.parametrize(("slots", "expected"), [(16, 3), (32, 6), (4, 1), (1, 1)])
def test_the_automatic_limit_is_slots_over_the_widest_step(
    monkeypatch, slots, expected
):
    monkeypatch.setattr(scan_admission, "widest_step", lambda: 5)
    monkeypatch.setattr(scan_admission.worker_presence, "stage_slots", lambda: slots)
    assert scan_admission.automatic_limit() == expected


def test_a_set_limit_wins_over_the_automatic_one(monkeypatch):
    monkeypatch.setattr(scan_admission, "automatic_limit", lambda: 3)
    assert scan_admission.resolve(0) == 3
    assert scan_admission.resolve(None) == 3
    assert scan_admission.resolve(7) == 7
