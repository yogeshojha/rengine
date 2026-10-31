from __future__ import annotations

from datetime import timedelta

import pytest

from app.services.service_timeline import ServiceTimelineService
from shared.definitions.timeline import (
    AddressFlag,
    AddressState,
    LaneState,
    Observation,
    PortFlag,
    ServiceTimelineMode,
)
from shared.models.timeline import ServiceTimelineFilter

pytestmark = pytest.mark.api

RAN = {
    "subdomain_discovery": "success",
    "http_probe": "success",
    "port_scan": "success",
}
NO_PORTS = {"subdomain_discovery": "success", "http_probe": "success"}
PARTIAL = {**RAN, "port_scan": "partial"}

A = "10.0.0.1"
B = "10.0.0.2"
WEB = [(A, 80, "http"), (A, 443, "https")]


async def _runs(estate, now, count: int, stages=RAN):
    stamps = [now - timedelta(days=count - 1 - i) for i in range(count)]
    for i, at in enumerate(stamps):
        await estate.scan("example.com", f"run{i}", at=at)
        await estate.activity(f"run{i}", stages)
    return stamps


async def _search(estate, scan: str, **kw):
    return await ServiceTimelineService(estate.session).search(
        estate.project_id, estate.scans[scan], ServiceTimelineFilter(**kw)
    )


def _address(result, ip: str):
    return next(r for r in result.addresses if r.ip == ip)


def _lane(row, port: int):
    return next(lane for lane in row.lanes if lane.port == port)


def _states(cells) -> list[str]:
    return [c.state for c in cells]


async def test_a_run_without_a_port_scan_is_not_observed(estate, now):
    stamps = await _runs(estate, now, 2, NO_PORTS)
    await estate.ports("run1", WEB, at=stamps[1])

    result = await _search(estate, "run1")

    assert [s.observation for s in result.scans] == [Observation.UNOBSERVED.value] * 2
    assert result.total == 0


async def test_a_port_opening_on_a_known_address_is_an_event(estate, now):
    stamps = await _runs(estate, now, 3)
    await estate.ports("run0", WEB, at=stamps[0])
    await estate.ports("run1", WEB, at=stamps[1])
    await estate.ports("run2", [*WEB, (A, 3306, "mysql")], at=stamps[2])

    result = await _search(estate, "run2")

    a = _address(result, A)
    assert _states(a.cells) == [
        AddressState.FIRST.value,
        AddressState.SAME.value,
        AddressState.OPENED.value,
    ]
    assert [c.port for c in a.cells[2].opened] == [3306]
    assert a.cells[2].opened[0].first_on_target is True
    assert a.changes == 1
    assert a.open_now == 3
    assert a.last_change_scan_id == estate.scans["run2"]
    assert AddressFlag.OPENED.value in a.flags
    assert result.counts[AddressFlag.OPENED.value] == 1
    lane = _lane(a, 3306)
    assert _states(lane.cells) == [
        LaneState.UNSEEN.value,
        LaneState.UNSEEN.value,
        LaneState.OPEN.value,
    ]
    assert lane.opened_scan_id == estate.scans["run2"]
    assert lane.open_now is True


async def test_a_port_closing_is_an_event_with_how_long_it_was_open(estate, now):
    stamps = await _runs(estate, now, 3)
    await estate.ports("run0", [*WEB, (A, 21, "ftp")], at=stamps[0])
    await estate.ports("run1", [*WEB, (A, 21, "ftp")], at=stamps[1])
    await estate.ports("run2", WEB, at=stamps[2])

    a = _address(await _search(estate, "run2"), A)

    assert a.cells[2].state == AddressState.CLOSED.value
    closed = a.cells[2].closed[0]
    assert closed.port == 21
    assert closed.open_since == stamps[0]
    lane = _lane(a, 21)
    assert _states(lane.cells) == [LaneState.OPEN.value] * 2 + [LaneState.CLOSED.value]
    assert lane.closed_scan_id == estate.scans["run2"]
    assert lane.open_now is False
    assert AddressFlag.CLOSED.value in a.flags
    assert a.open_now == 2


async def test_an_address_first_seen_is_not_a_port_opening(estate, now):
    stamps = await _runs(estate, now, 2)
    await estate.ports("run0", WEB, at=stamps[0])
    await estate.ports("run1", [*WEB, (B, 22, "ssh")], at=stamps[1])

    result = await _search(estate, "run1")

    b = _address(result, B)
    assert _states(b.cells) == [AddressState.UNSEEN.value, AddressState.FIRST.value]
    assert b.changes == 0
    assert AddressFlag.NEW.value in b.flags
    assert AddressFlag.OPENED.value not in b.flags
    assert result.counts[AddressFlag.NEW.value] == 1


async def test_an_address_with_no_ports_left_is_gone(estate, now):
    stamps = await _runs(estate, now, 3)
    await estate.ports("run0", [(B, 22, "ssh")], at=stamps[0])
    await estate.ports("run1", WEB, at=stamps[1])
    await estate.ports("run2", WEB, at=stamps[2])

    result = await _search(estate, "run2")

    b = _address(result, B)
    assert _states(b.cells) == [
        AddressState.FIRST.value,
        AddressState.CLOSED.value,
        AddressState.GONE.value,
    ]
    assert AddressFlag.GONE.value in b.flags
    assert b.open_now == 0


async def test_a_partial_port_scan_does_not_close_a_port(estate, now):
    stamps = await _runs(estate, now, 3, PARTIAL)
    await estate.ports("run0", [*WEB, (A, 22, "ssh")], at=stamps[0])
    await estate.ports("run1", WEB, at=stamps[1])
    await estate.ports("run2", [*WEB, (A, 22, "ssh")], at=stamps[2])

    a = _address(await _search(estate, "run2"), A)

    assert _states(_lane(a, 22).cells) == [
        LaneState.OPEN.value,
        LaneState.UNCONFIRMED.value,
        LaneState.OPEN.value,
    ]
    assert a.changes == 0
    assert _states(a.cells) == [
        AddressState.FIRST.value,
        AddressState.SAME.value,
    ] * 1 + [AddressState.SAME.value]


async def test_software_change_is_counted_and_marked_on_the_lane(estate, now):
    stamps = await _runs(estate, now, 2)
    await estate.ports(
        "run0", [(A, 22, "ssh")], at=stamps[0], product="OpenSSH", version="8.9"
    )
    await estate.ports(
        "run1", [(A, 22, "ssh")], at=stamps[1], product="OpenSSH", version="9.6"
    )

    a = _address(await _search(estate, "run1"), A)

    assert AddressFlag.SOFTWARE.value in a.flags
    assert a.changes == 1
    lane = _lane(a, 22)
    assert lane.software_changes == 1
    assert lane.cells[1].software_changed is True
    assert [c.port for c in a.cells[1].software] == [22]


async def test_a_port_that_keeps_changing_is_flagged(estate, now):
    stamps = await _runs(estate, now, 5)
    for i, present in enumerate((True, False, True, False, True)):
        await estate.ports(
            f"run{i}", [*WEB, *([(A, 9418, "git")] if present else [])], at=stamps[i]
        )

    a = _address(await _search(estate, "run4"), A)

    assert _lane(a, 9418).events == 4
    assert AddressFlag.FLAPPING.value in a.flags


async def test_the_query_narrows_the_lanes_and_the_counts(estate, now):
    stamps = await _runs(estate, now, 2)
    await estate.ports("run0", WEB, at=stamps[0])
    await estate.ports("run1", [*WEB, (A, 3306, "mysql"), (B, 22, "ssh")], at=stamps[1])

    result = await _search(estate, "run1", q="port:3306")

    assert result.total == 1
    a = _address(result, A)
    assert [lane.port for lane in a.lanes] == [3306]
    assert result.counts[AddressFlag.OPENED.value] == 1


async def test_by_port_counts_addresses_per_run_and_their_change(estate, now):
    stamps = await _runs(estate, now, 3)
    await estate.ports("run0", WEB, at=stamps[0])
    await estate.ports("run1", [*WEB, (A, 3306, "mysql")], at=stamps[1])
    await estate.ports(
        "run2", [*WEB, (A, 3306, "mysql"), (B, 3306, "mysql")], at=stamps[2]
    )

    result = await _search(estate, "run2", mode=ServiceTimelineMode.PORT.value)

    row = next(r for r in result.ports if r.port == 3306)
    assert [c.count for c in row.cells] == [0, 1, 2]
    assert [c.delta for c in row.cells] == [0, 1, 1]
    assert row.cells[2].added == [B]
    assert row.now == 2
    assert row.peak == 2
    assert row.first_seen_at == stamps[1]
    assert row.last_change_scan_id == estate.scans["run2"]
    assert PortFlag.SPREAD.value in row.flags
    assert result.counts[PortFlag.SPREAD.value] == 1
    spread = await _search(
        estate, "run2", mode=ServiceTimelineMode.PORT.value, flag=PortFlag.SPREAD.value
    )
    assert [r.port for r in spread.ports] == [3306]


async def test_by_port_gone_and_new_on_target(estate, now):
    stamps = await _runs(estate, now, 3)
    await estate.ports("run0", [*WEB, (A, 21, "ftp")], at=stamps[0])
    await estate.ports("run1", WEB, at=stamps[1])
    await estate.ports("run2", [*WEB, (A, 8443, "https")], at=stamps[2])

    result = await _search(estate, "run2", mode=ServiceTimelineMode.PORT.value)

    ftp = next(r for r in result.ports if r.port == 21)
    assert PortFlag.GONE.value in ftp.flags
    assert ftp.now == 0
    alt = next(r for r in result.ports if r.port == 8443)
    assert PortFlag.NEW.value in alt.flags
    assert result.counts[PortFlag.GONE.value] == 1
    assert result.counts[PortFlag.NEW.value] == 1
