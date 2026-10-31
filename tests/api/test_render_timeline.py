from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import text

from app.services.render_timeline import RenderTimelineService
from shared.definitions.timeline import (
    FLAPPING_TRANSITIONS,
    Observation,
    RenderFlag,
    RenderState,
)
from shared.models.timeline import RenderFilter

pytestmark = pytest.mark.api

RAN = {
    "subdomain_discovery": "success",
    "http_probe": "success",
    "screenshot": "success",
}
RAN_WEB = {"subdomain_discovery": "success", "http_probe": "success"}
PARTIAL = {**RAN, "screenshot": "partial"}

A = "a.example.com"
B = "b.example.com"
C = "c.example.com"
IPS = ["10.0.0.1"]
H1 = 0x5A5A_5A5A_5A5A_5A5A
H1_NEAR = H1 ^ 0b1
H2 = H1 ^ 0b1111
H3 = H2 ^ 0b111_000


async def _runs(estate, now, count: int, stages=RAN):
    stamps = [now - timedelta(days=count - 1 - i) for i in range(count)]
    for i, at in enumerate(stamps):
        await estate.scan("example.com", f"run{i}", at=at)
        await estate.activity(f"run{i}", stages)
    return stamps


async def _search(estate, scan: str, **kw):
    return await RenderTimelineService(estate.session).search(
        estate.project_id, estate.scans[scan], RenderFilter(**kw)
    )


def _row(result, name: str):
    return next(r for r in result.items if r.host.name == name)


def _states(row) -> list[str]:
    return [c.state for c in row.cells]


async def test_a_run_without_the_screenshot_stage_is_not_observed(estate, now):
    stamps = await _runs(estate, now, 2, RAN_WEB)
    await estate.hosts("run1", [A], at=stamps[1], ips=IPS, status=200, phash=H1)

    result = await _search(estate, "run1")

    assert [s.observation for s in result.scans] == [Observation.UNOBSERVED.value] * 2
    assert result.total == 0


async def test_a_capture_is_first_then_same_then_changed(estate, now):
    stamps = await _runs(estate, now, 4)
    for i, phash in enumerate((None, H1, H1_NEAR, H2)):
        await estate.hosts(
            f"run{i}", [A], at=stamps[i], ips=IPS, status=200, phash=phash
        )

    result = await _search(estate, "run3")

    a = _row(result, A)
    assert _states(a) == [
        RenderState.NOT_CAPTURED.value,
        RenderState.FIRST.value,
        RenderState.SAME.value,
        RenderState.CHANGED.value,
    ]
    assert [c.distance for c in a.cells] == [None, None, 1, 3]
    assert a.changes == 1
    assert a.first_capture_at == stamps[1]
    assert a.last_change_scan_id == estate.scans["run3"]
    assert RenderFlag.CHANGED.value in a.flags
    assert a.cells[3].path is not None


async def test_the_first_capture_is_the_last_change_until_one_happens(estate, now):
    stamps = await _runs(estate, now, 3)
    await estate.hosts("run0", [A], at=stamps[0], ips=IPS, status=200)
    await estate.hosts("run1", [A], at=stamps[1], ips=IPS, status=200, phash=H1)
    await estate.hosts("run2", [A], at=stamps[2], ips=IPS, status=200, phash=H1)

    a = _row(await _search(estate, "run2"), A)

    assert a.changes == 0
    assert a.last_change_scan_id == estate.scans["run1"]
    assert RenderFlag.CHANGED.value not in a.flags


async def test_new_render_is_first_captured_in_the_viewed_scan(estate, now):
    stamps = await _runs(estate, now, 2)
    await estate.hosts("run0", [A, B], at=stamps[0], ips=IPS, status=200)
    await estate.hosts("run1", [A], at=stamps[1], ips=IPS, status=200, phash=H1)
    await estate.hosts("run1", [B], at=stamps[1], ips=IPS, status=200)

    result = await _search(estate, "run1")

    assert RenderFlag.NEW.value in _row(result, A).flags
    assert RenderFlag.NOT_CAPTURED.value in _row(result, B).flags
    assert result.counts[RenderFlag.NEW.value] == 1
    assert result.counts[RenderFlag.NOT_CAPTURED.value] == 1
    new = await _search(estate, "run1", flag=RenderFlag.NEW.value)
    assert [r.host.name for r in new.items] == [A]
    assert new.total == 1


async def test_an_expired_image_still_compares_and_is_flagged(estate, now):
    stamps = await _runs(estate, now, 2)
    await estate.hosts("run0", [A], at=stamps[0], ips=IPS, status=200, phash=H1)
    await estate.hosts("run1", [A], at=stamps[1], ips=IPS, status=200, phash=H2)
    await estate.session.execute(
        text("UPDATE subdomains SET screenshot_path = NULL WHERE scan_id = :sid"),
        {"sid": estate.scans["run0"]},
    )

    a = _row(await _search(estate, "run1"), A)

    assert _states(a) == [RenderState.FIRST.value, RenderState.CHANGED.value]
    assert a.cells[0].path is None
    assert RenderFlag.EXPIRED.value in a.flags


async def test_flapping_is_three_render_changes(estate, now):
    stamps = await _runs(estate, now, 4)
    for i, phash in enumerate((H1, H2, H1, H2)):
        await estate.hosts(
            f"run{i}", [A], at=stamps[i], ips=IPS, status=200, phash=phash
        )

    result = await _search(estate, "run3")

    a = _row(result, A)
    assert a.changes == FLAPPING_TRANSITIONS
    assert RenderFlag.FLAPPING.value in a.flags
    assert result.counts[RenderFlag.FLAPPING.value] == 1


async def test_absences_and_hosts_without_http(estate, now):
    stamps = await _runs(estate, now, 3)
    await estate.hosts("run0", [A], at=stamps[0], ips=IPS, status=200, phash=H1)
    await estate.hosts("run1", [A], at=stamps[1], ips=IPS)
    await estate.hosts("run0", [C], at=stamps[0])
    await estate.hosts("run1", [C], at=stamps[1])
    await estate.hosts("run2", [C], at=stamps[2])

    result = await _search(estate, "run2")

    assert _states(_row(result, A)) == [
        RenderState.FIRST.value,
        RenderState.NO_HTTP.value,
        RenderState.GONE.value,
    ]
    assert all(r.host.name != C for r in result.items)
    assert result.total == 1


async def test_a_partial_capture_does_not_confirm_an_absence(estate, now):
    stamps = await _runs(estate, now, 2, PARTIAL)
    await estate.hosts("run0", [A], at=stamps[0], ips=IPS, status=200, phash=H1)
    await estate.hosts("run1", [A], at=stamps[1], ips=IPS, status=200)

    a = _row(await _search(estate, "run1"), A)

    assert _states(a) == [RenderState.FIRST.value, RenderState.UNCONFIRMED.value]
    assert RenderFlag.NOT_CAPTURED.value in a.flags


async def test_the_query_narrows_the_rows_and_the_counts(estate, now):
    stamps = await _runs(estate, now, 2)
    await estate.hosts("run0", [A, B], at=stamps[0], ips=IPS, status=200, phash=H1)
    await estate.hosts("run1", [A], at=stamps[1], ips=IPS, status=200, phash=H2)
    await estate.hosts("run1", [B], at=stamps[1], ips=IPS, status=404, phash=H3)

    whole = await _search(estate, "run1")
    narrowed = await _search(estate, "run1", q="status:4xx")

    assert whole.total == whole.counts[RenderFlag.CHANGED.value] == 2
    assert narrowed.total == narrowed.counts[RenderFlag.CHANGED.value] == 1
    assert [r.host.name for r in narrowed.items] == [B]


async def test_sorted_by_changes_puts_the_busiest_host_first(estate, now):
    stamps = await _runs(estate, now, 3)
    for i, phash in enumerate((H1, H2, H3)):
        await estate.hosts(
            f"run{i}", [A], at=stamps[i], ips=IPS, status=200, phash=phash
        )
        await estate.hosts(f"run{i}", [B], at=stamps[i], ips=IPS, status=200, phash=H1)

    result = await _search(estate, "run2", sort="changes", order="desc")

    assert [r.host.name for r in result.items] == [A, B]
    assert [r.changes for r in result.items] == [2, 0]
