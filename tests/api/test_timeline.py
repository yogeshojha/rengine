from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi import HTTPException

from app.services.timeline import TimelineService, observation_of
from shared.definitions.timeline import (
    FLAPPING_TRANSITIONS,
    Observation,
    TimelineFlag,
    WebAssetState,
)
from shared.models.timeline import TimelineFilter

pytestmark = pytest.mark.api

RAN_WEB = {"subdomain_discovery": "success", "http_probe": "success"}
PARTIAL_WEB = {"subdomain_discovery": "partial", "http_probe": "success"}
CANCELLED_WEB = {"subdomain_discovery": "success", "http_probe": "aborted"}

A = "a.example.com"
B = "b.example.com"
C = "c.example.com"
D = "d.example.com"
IPS = ["10.0.0.1"]


async def _runs(estate, now, count: int, *, status: str = "completed"):
    """`count` census runs a day apart, the last one at `now`."""
    stamps = [now - timedelta(days=count - 1 - i) for i in range(count)]
    for i, at in enumerate(stamps):
        await estate.scan("example.com", f"run{i}", at=at, status=status)
        await estate.activity(f"run{i}", RAN_WEB)
    return stamps


def _row(result, name: str):
    return next(r for r in result.items if r.host.name == name)


def _states(row) -> list[str]:
    return [c.state for c in row.cells]


async def _search(estate, scan: str, **kw):
    return await TimelineService(estate.session).search(
        estate.project_id, estate.scans[scan], TimelineFilter(**kw)
    )


async def test_columns_are_the_census_runs_up_to_the_viewed_one(estate, now):
    stamps = await _runs(estate, now, 3)
    later = await estate.scan("example.com", "later", at=now + timedelta(days=1))
    await estate.activity("later", RAN_WEB)
    await estate.hosts("run2", [A], at=stamps[2], ips=IPS, status=200)

    result = await _search(estate, "run2")

    assert [c.id for c in result.scans] == [estate.scans[f"run{i}"] for i in range(3)]
    assert later not in {c.id for c in result.scans}
    assert all(c.observation == Observation.OBSERVED.value for c in result.scans)


async def test_a_focused_run_has_no_timeline(estate, now):
    await estate.scan("example.com", "focused", at=now, scope="focused")

    with pytest.raises(HTTPException) as exc:
        await _search(estate, "focused")

    assert exc.value.status_code == 422


async def test_a_host_new_in_the_viewed_scan_starts_unseen(estate, now):
    stamps = await _runs(estate, now, 3)
    for i in range(3):
        await estate.hosts(f"run{i}", [A], at=stamps[i], ips=IPS, status=200)
    await estate.hosts("run2", [B], at=stamps[2], ips=IPS, status=200)

    result = await _search(estate, "run2")

    b = _row(result, B)
    assert _states(b) == [
        WebAssetState.UNSEEN.value,
        WebAssetState.UNSEEN.value,
        WebAssetState.LIVE.value,
    ]
    assert TimelineFlag.NEW.value in b.flags
    assert b.first_seen_at == stamps[2]
    assert result.counts[TimelineFlag.NEW.value] == 1
    assert TimelineFlag.NEW.value not in _row(result, A).flags


async def test_a_host_absent_from_a_clean_run_is_gone_and_still_a_row(estate, now):
    stamps = await _runs(estate, now, 3)
    await estate.hosts("run0", [A, B], at=stamps[0], ips=IPS, status=200)
    await estate.hosts("run1", [A, B], at=stamps[1], ips=IPS, status=200)
    await estate.hosts("run2", [A], at=stamps[2], ips=IPS, status=200)

    result = await _search(estate, "run2")

    assert result.total == 2
    b = _row(result, B)
    assert b.state == WebAssetState.GONE.value
    assert _states(b)[-1] == WebAssetState.GONE.value
    assert TimelineFlag.GONE.value in b.flags
    assert b.host.scan_id == estate.scans["run1"]
    assert result.counts[TimelineFlag.GONE.value] == 1


async def test_absence_from_a_partial_discovery_is_not_confirmed(estate, now):
    stamps = await _runs(estate, now, 3)
    await estate.activity("run1", PARTIAL_WEB)
    await estate.hosts("run0", [A], at=stamps[0], ips=IPS, status=200)
    await estate.hosts("run2", [A], at=stamps[2], ips=IPS, status=200)

    result = await _search(estate, "run2")

    a = _row(result, A)
    assert result.scans[1].observation == Observation.PARTIAL.value
    assert _states(a) == [
        WebAssetState.LIVE.value,
        WebAssetState.UNCONFIRMED.value,
        WebAssetState.LIVE.value,
    ]
    assert a.transitions == 0
    assert TimelineFlag.CHANGED.value not in a.flags


async def test_a_run_whose_probe_did_not_finish_is_not_observed(estate, now):
    stamps = await _runs(estate, now, 3)
    await estate.activity("run1", CANCELLED_WEB)
    await estate.hosts("run0", [A], at=stamps[0], ips=IPS, status=200)
    await estate.hosts("run1", [A], at=stamps[1], ips=IPS)
    await estate.hosts("run2", [A], at=stamps[2], ips=IPS, status=200)

    result = await _search(estate, "run2")

    assert result.scans[1].observation == Observation.UNOBSERVED.value
    a = _row(result, A)
    assert _states(a)[1] == WebAssetState.UNOBSERVED.value
    assert a.transitions == 0


async def test_an_unobserved_run_before_the_first_sighting_stays_unseen(estate, now):
    stamps = await _runs(estate, now, 3)
    await estate.activity("run0", CANCELLED_WEB)
    await estate.hosts("run1", [A], at=stamps[1], ips=IPS, status=200)
    await estate.hosts("run2", [A], at=stamps[2], ips=IPS, status=200)

    result = await _search(estate, "run2")

    assert _states(_row(result, A))[0] == WebAssetState.UNSEEN.value


async def test_status_changes_are_transitions_with_the_last_one_named(estate, now):
    stamps = await _runs(estate, now, 4)
    for i, status in enumerate((200, 404, 404, 200)):
        await estate.hosts(f"run{i}", [A], at=stamps[i], ips=IPS, status=status)

    result = await _search(estate, "run3")

    a = _row(result, A)
    assert _states(a) == [
        WebAssetState.LIVE.value,
        WebAssetState.CLIENT_ERROR.value,
        WebAssetState.CLIENT_ERROR.value,
        WebAssetState.LIVE.value,
    ]
    assert a.transitions == 2
    assert a.last_change_scan_id == estate.scans["run3"]
    assert TimelineFlag.CHANGED.value in a.flags
    assert TimelineFlag.FLAPPING.value not in a.flags


async def test_flapping_is_three_transitions_in_the_window(estate, now):
    stamps = await _runs(estate, now, 4)
    for i, status in enumerate((200, 404, 200, 404)):
        await estate.hosts(f"run{i}", [A], at=stamps[i], ips=IPS, status=status)

    result = await _search(estate, "run3")

    a = _row(result, A)
    assert a.transitions == FLAPPING_TRANSITIONS
    assert TimelineFlag.FLAPPING.value in a.flags
    assert result.counts[TimelineFlag.FLAPPING.value] == 1


async def test_ephemeral_is_appeared_and_gone_inside_the_window(estate, now):
    stamps = await _runs(estate, now, 4)
    for i in range(4):
        await estate.hosts(f"run{i}", [A], at=stamps[i], ips=IPS, status=200)
    await estate.hosts("run1", [B], at=stamps[1], ips=IPS, status=200)
    await estate.hosts("run2", [B], at=stamps[2], ips=IPS, status=200)

    result = await _search(estate, "run3")

    b = _row(result, B)
    assert _states(b) == [
        WebAssetState.UNSEEN.value,
        WebAssetState.LIVE.value,
        WebAssetState.LIVE.value,
        WebAssetState.GONE.value,
    ]
    assert TimelineFlag.EPHEMERAL.value in b.flags
    assert TimelineFlag.EPHEMERAL.value not in _row(result, A).flags
    assert result.counts[TimelineFlag.EPHEMERAL.value] == 1


async def test_an_attribute_change_with_the_state_unchanged_is_a_dot(estate, now):
    stamps = await _runs(estate, now, 2)
    await estate.hosts("run0", [A], at=stamps[0], ips=IPS, status=200, title="Portal")
    await estate.hosts(
        "run1", [A], at=stamps[1], ips=["10.0.0.2"], status=200, title="Maintenance"
    )

    result = await _search(estate, "run1")

    a = _row(result, A)
    assert a.transitions == 0
    assert a.attribute_changes == 1
    assert a.cells[1].changed == ["Title", "Addresses"]
    assert TimelineFlag.ATTRIBUTE.value in a.flags
    assert TimelineFlag.CHANGED.value in a.flags


async def test_address_order_is_not_a_change(estate, now):
    stamps = await _runs(estate, now, 2)
    await estate.hosts(
        "run0", [A], at=stamps[0], ips=["10.0.0.1", "10.0.0.2"], status=200
    )
    await estate.hosts(
        "run1", [A], at=stamps[1], ips=["10.0.0.2", "10.0.0.1"], status=200
    )

    result = await _search(estate, "run1")

    a = _row(result, A)
    assert a.attribute_changes == 0
    assert a.cells[1].changed == []


async def test_no_addresses_is_unresolved_and_no_status_is_no_http(estate, now):
    stamps = await _runs(estate, now, 3)
    await estate.hosts("run0", [A], at=stamps[0], ips=IPS, status=200)
    await estate.hosts("run1", [A], at=stamps[1], ips=IPS)
    await estate.hosts("run2", [A], at=stamps[2])

    result = await _search(estate, "run2")

    assert _states(_row(result, A)) == [
        WebAssetState.LIVE.value,
        WebAssetState.NO_HTTP.value,
        WebAssetState.UNRESOLVED.value,
    ]


async def test_the_flag_filter_returns_exactly_what_its_count_promised(estate, now):
    stamps = await _runs(estate, now, 3)
    await estate.hosts("run0", [A, B, C], at=stamps[0], ips=IPS, status=200)
    await estate.hosts("run1", [A, B, C], at=stamps[1], ips=IPS, status=200)
    await estate.hosts("run2", [A, B], at=stamps[2], ips=IPS, status=200)
    await estate.hosts("run2", [D], at=stamps[2], ips=IPS, status=200)

    whole = await _search(estate, "run2")
    changed = await _search(estate, "run2", flag=TimelineFlag.CHANGED.value)

    assert whole.total == whole.counts["all"] == 4
    assert whole.counts[TimelineFlag.CHANGED.value] == changed.total == 1
    assert {r.host.name for r in changed.items} == {C}
    assert whole.counts[TimelineFlag.NEW.value] == 1
    assert changed.counts == whole.counts


async def test_the_query_narrows_the_rows_and_the_counts(estate, now):
    stamps = await _runs(estate, now, 2)
    await estate.hosts("run0", [A, B], at=stamps[0], ips=IPS, status=200)
    await estate.hosts("run1", [A], at=stamps[1], ips=IPS, status=200)
    await estate.hosts("run1", [B], at=stamps[1], ips=IPS, status=404)

    result = await _search(estate, "run1", q="status:4xx")

    assert [r.host.name for r in result.items] == [B]
    assert result.counts[TimelineFlag.CHANGED.value] == 1
    assert result.counts[TimelineFlag.NEW.value] == 0


async def test_a_bad_query_is_an_error_not_a_failure(estate, now):
    await _runs(estate, now, 1)

    result = await _search(estate, "run0", q="status:>")

    assert result.error is not None
    assert result.items == []


async def test_sorted_by_last_change_puts_the_latest_change_first(estate, now):
    stamps = await _runs(estate, now, 3)
    await estate.hosts("run0", [A, B], at=stamps[0], ips=IPS, status=200)
    await estate.hosts("run1", [A], at=stamps[1], ips=IPS, status=404)
    await estate.hosts("run1", [B], at=stamps[1], ips=IPS, status=200)
    await estate.hosts("run2", [A], at=stamps[2], ips=IPS, status=404)
    await estate.hosts("run2", [B], at=stamps[2], ips=IPS, status=500)

    result = await _search(estate, "run2")

    assert [r.host.name for r in result.items] == [B, A]


async def test_the_window_cuts_the_columns_and_the_counts(estate, now):
    stamps = await _runs(estate, now, 4)
    await estate.hosts("run0", [A], at=stamps[0], ips=IPS, status=200)
    await estate.hosts("run1", [A], at=stamps[1], ips=IPS, status=404)
    await estate.hosts("run2", [A], at=stamps[2], ips=IPS, status=404)
    await estate.hosts("run3", [A], at=stamps[3], ips=IPS, status=404)

    result = await _search(estate, "run3", window=2)

    assert [c.id for c in result.scans] == [estate.scans["run2"], estate.scans["run3"]]
    assert _row(result, A).transitions == 0


async def test_a_holding_run_without_stages_is_not_a_column(estate, now):
    stamps = await _runs(estate, now, 2)
    await estate.scan("example.com", "holding", at=stamps[0] + timedelta(hours=1))
    await estate.hosts("run0", [A], at=stamps[0], ips=IPS, status=200)
    await estate.hosts("run1", [A], at=stamps[1], ips=IPS, status=200)

    result = await _search(estate, "run1")

    assert estate.scans["holding"] not in {c.id for c in result.scans}


def test_observation_needs_every_observing_stage_to_finish():
    assert observation_of({}) == Observation.UNOBSERVED.value
    assert observation_of({"subdomain_discovery": "success"}) == (
        Observation.UNOBSERVED.value
    )
    assert observation_of(RAN_WEB) == Observation.OBSERVED.value
    assert observation_of(PARTIAL_WEB) == Observation.PARTIAL.value
    assert observation_of(CANCELLED_WEB) == Observation.UNOBSERVED.value
