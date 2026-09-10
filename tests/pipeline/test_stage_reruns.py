"""A stage that already finished must never be dispatched a second time."""

from __future__ import annotations

import pytest

from shared.enums.scan import ScanActivityStatus
from shared.models.scan_activity import ScanActivity
from shared.services.orchestrator.tracking import ScanActivityService

pytestmark = pytest.mark.pipeline

TERMINAL = (
    ScanActivityStatus.SUCCESS.value,
    ScanActivityStatus.PARTIAL.value,
)
RERUNNABLE = (
    ScanActivityStatus.RUNNING.value,
    ScanActivityStatus.FAILED.value,
    ScanActivityStatus.SKIPPED.value,
    ScanActivityStatus.ABORTED.value,
)


async def _activity(estate, scan: str, name: str, status: str) -> None:
    estate.session.add(
        ScanActivity(
            scan_id=estate.scans[scan],
            project_id=estate.project_id,
            name=name,
            title=name,
            status=status,
        )
    )
    await estate.session.flush()


async def _finished(estate, scan: str, name: str):
    return await estate.session.run_sync(
        lambda s: ScanActivityService(s).finished(estate.scans[scan], name)
    )


@pytest.mark.parametrize("status", TERMINAL)
async def test_a_finished_stage_is_recognised(estate, now, status):
    await estate.scan("example.com", "run", at=now)
    await _activity(estate, "run", "http_probe", status)

    assert await _finished(estate, "run", "http_probe") is not None


@pytest.mark.parametrize("status", RERUNNABLE)
async def test_an_unfinished_stage_may_run(estate, now, status):
    """A killed worker leaves RUNNING, and a failure must stay retryable."""
    await estate.scan("example.com", "run", at=now)
    await _activity(estate, "run", "http_probe", status)

    assert await _finished(estate, "run", "http_probe") is None


async def test_another_scan_of_the_same_target_is_unaffected(estate, now):
    """The guard is per scan; a rescan runs every stage again."""
    await estate.scan("example.com", "first", at=now)
    await estate.scan("example.com", "second", at=now)
    await _activity(estate, "first", "http_probe", ScanActivityStatus.SUCCESS.value)

    assert await _finished(estate, "first", "http_probe") is not None
    assert await _finished(estate, "second", "http_probe") is None


async def test_another_stage_in_the_same_scan_is_unaffected(estate, now):
    await estate.scan("example.com", "run", at=now)
    await _activity(estate, "run", "http_probe", ScanActivityStatus.SUCCESS.value)

    assert await _finished(estate, "run", "port_scan") is None
