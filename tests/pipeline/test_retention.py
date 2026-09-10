"""Retention deletes, so what it must NOT delete is the part worth testing."""

from __future__ import annotations

from datetime import timedelta

import pytest
import sqlalchemy as sa

from shared.enums.scan import ScanStatus
from shared.models.instance_settings import InstanceSettings
from shared.models.scan import Scan
from shared.models.subdomain import Subdomain
from shared.services import retention

pytestmark = pytest.mark.pipeline


async def _windows(session, *, scans: int, shots: int) -> None:
    session.add(
        InstanceSettings(
            singleton_key="instance",
            scan_history_retention_days=scans,
            screenshot_retention_days=shots,
        )
    )
    await session.flush()


async def _run(durable_estate, **windows) -> retention.RetentionResult:
    await _windows(durable_estate.session, **windows)
    return await durable_estate.session.run_sync(retention.enforce)


async def _scan_ids(session) -> set:
    return set(await session.scalars(sa.select(Scan.id)))


async def test_a_run_inside_the_window_is_kept(durable_estate, now):
    await durable_estate.scan("example.com", "recent", at=now - timedelta(days=5))
    await durable_estate.hosts("recent", ["a.example.com"], at=now - timedelta(days=5))

    result = await _run(durable_estate, scans=90, shots=30)

    assert result.scans_removed == 0
    assert durable_estate.scans["recent"] in await _scan_ids(durable_estate.session)


async def test_a_run_past_the_window_goes_with_its_rows(durable_estate, now):
    old = now - timedelta(days=200)
    await durable_estate.scan("example.com", "ancient", at=old)
    await durable_estate.hosts("ancient", ["a.example.com", "b.example.com"], at=old)
    await durable_estate.scan("example.com", "recent", at=now)
    await durable_estate.hosts("recent", ["a.example.com"], at=now)

    result = await _run(durable_estate, scans=90, shots=30)

    assert result.scans_removed == 1
    remaining = await _scan_ids(durable_estate.session)
    assert durable_estate.scans["ancient"] not in remaining
    assert durable_estate.scans["recent"] in remaining
    left = await durable_estate.session.scalars(
        sa.select(Subdomain.id).where(
            Subdomain.scan_id == durable_estate.scans["ancient"]
        )
    )
    assert not list(left), "the scan's rows must cascade away with it"


async def test_a_target_never_loses_its_only_run(durable_estate, now):
    """'Not scanned' must mean never scanned, never 'scanned and then pruned'."""
    old = now - timedelta(days=400)
    await durable_estate.scan("example.com", "only", at=old)
    await durable_estate.hosts("only", ["a.example.com"], at=old)

    result = await _run(durable_estate, scans=90, shots=30)

    assert result.scans_removed == 0
    assert result.scans_kept_newest == 1
    assert durable_estate.scans["only"] in await _scan_ids(durable_estate.session)


async def test_a_running_scan_is_never_deleted(durable_estate, now):
    """An old queued or running row is work in flight, not history."""
    old = now - timedelta(days=400)
    await durable_estate.scan("example.com", "keeper", at=now)
    await durable_estate.scan(
        "example.com", "inflight", at=old, status=ScanStatus.RUNNING.value
    )

    result = await _run(durable_estate, scans=90, shots=30)

    assert result.scans_removed == 0
    assert durable_estate.scans["inflight"] in await _scan_ids(durable_estate.session)


async def test_zero_keeps_everything(durable_estate, now):
    """0 is how an operator opts out; it must not read as 'delete everything'."""
    old = now - timedelta(days=4000)
    await durable_estate.scan("example.com", "ancient", at=old)
    await durable_estate.scan("example.com", "recent", at=now)

    result = await _run(durable_estate, scans=0, shots=0)

    assert result.scans_removed == 0
    assert result.media_removed == 0
    assert len(await _scan_ids(durable_estate.session)) == 2


async def test_each_target_keeps_its_own_newest(durable_estate, now):
    old = now - timedelta(days=400)
    older = now - timedelta(days=800)
    for target in ("one.com", "two.com"):
        await durable_estate.scan(target, f"{target}-old", at=older)
        await durable_estate.scan(target, f"{target}-new", at=old)

    result = await _run(durable_estate, scans=90, shots=30)

    assert result.scans_removed == 2
    assert result.scans_kept_newest == 2
    remaining = await _scan_ids(durable_estate.session)
    assert durable_estate.scans["one.com-new"] in remaining
    assert durable_estate.scans["two.com-new"] in remaining
    assert durable_estate.scans["one.com-old"] not in remaining
    assert durable_estate.scans["two.com-old"] not in remaining
