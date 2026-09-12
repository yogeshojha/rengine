from __future__ import annotations

import pytest

from shared.enums.scan import ScanActivityStatus, ScanStatus
from shared.models.scan_activity import ScanActivity
from shared.services.orchestrator import aggregate_status, stages_done

pytestmark = pytest.mark.pipeline

TERMINAL = (
    ScanActivityStatus.SUCCESS.value,
    ScanActivityStatus.PARTIAL.value,
    ScanActivityStatus.FAILED.value,
    ScanActivityStatus.SKIPPED.value,
    ScanActivityStatus.ABORTED.value,
)


def _row(name: str, status: str) -> ScanActivity:
    return ScanActivity(name=name, title=name, status=status)


@pytest.mark.parametrize("status", TERMINAL)
def test_a_settled_stage_is_done(status):
    assert stages_done([_row("http_probe", status)]) == {"http_probe"}


def test_a_running_stage_is_not_done():
    assert stages_done([_row("http_probe", ScanActivityStatus.RUNNING.value)]) == set()


def test_a_superseded_row_does_not_make_a_stranded_stage_done():
    rows = [
        _row("subdomain_discovery", ScanActivityStatus.SKIPPED.value),
        _row("subdomain_discovery", ScanActivityStatus.RUNNING.value),
        _row("http_probe", ScanActivityStatus.SUCCESS.value),
    ]

    assert stages_done(rows) == {"http_probe"}


def test_an_earlier_success_does_not_make_a_stranded_stage_done():
    rows = [
        _row("subdomain_discovery", ScanActivityStatus.SUCCESS.value),
        _row("subdomain_discovery", ScanActivityStatus.RUNNING.value),
    ]

    assert stages_done(rows) == set()


@pytest.mark.parametrize(
    "rows",
    [
        [
            _row("subdomain_discovery", ScanActivityStatus.SKIPPED.value),
            _row("subdomain_discovery", ScanActivityStatus.RUNNING.value),
        ],
        [
            _row("subdomain_discovery", ScanActivityStatus.SUCCESS.value),
            _row("subdomain_discovery", ScanActivityStatus.RUNNING.value),
            _row("http_probe", ScanActivityStatus.SUCCESS.value),
        ],
    ],
)
def test_the_resumer_and_finalize_never_disagree(rows):
    """Whatever finalize still calls RUNNING, the resumer must still call unfinished."""
    running = aggregate_status(rows) == ScanStatus.RUNNING.value
    names = {row.name for row in rows}

    assert running is bool(names - stages_done(rows))
