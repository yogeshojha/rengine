from __future__ import annotations

import pytest

from shared.enums.scan import ScanActivityStatus, ScanStatus
from shared.models.scan_activity import ScanActivity
from shared.services.orchestrator import aggregate_status, stages_done, superseded
from stages.registry import ordered_levels, resume_level

pytestmark = pytest.mark.pipeline


def _row(name: str, status: str) -> ScanActivity:
    return ScanActivity(name=name, title=name, status=status)


def _names(level: int) -> set[str]:
    return {spec.name for lvl in ordered_levels()[:level] for spec in lvl}


def test_a_paused_stage_is_not_done():
    assert stages_done([_row("http_probe", ScanActivityStatus.PAUSED.value)]) == set()


def test_a_paused_stage_leaves_the_run_unsettled():
    rows = [
        _row("subdomain_discovery", ScanActivityStatus.SUCCESS.value),
        _row("http_probe", ScanActivityStatus.PAUSED.value),
    ]

    assert aggregate_status(rows) == ScanStatus.RUNNING.value


def test_a_superseded_paused_row_does_not_cancel_the_resumed_run():
    """The pause leaves a row behind; the re-run supersedes it, and the verdict is its own."""
    rows = [
        _row("http_probe", ScanActivityStatus.SKIPPED.value),
        _row("http_probe", ScanActivityStatus.SUCCESS.value),
    ]

    assert aggregate_status(rows) == ScanStatus.COMPLETED.value
    assert stages_done(rows) == {"http_probe"}


def test_an_aborted_stage_still_cancels_the_run():
    rows = [_row("http_probe", ScanActivityStatus.ABORTED.value)]

    assert aggregate_status(rows) == ScanStatus.CANCELLED.value


def test_a_run_with_nothing_done_resumes_at_the_first_level():
    assert resume_level(frozenset()) == 0


def test_a_run_with_every_stage_done_resumes_past_the_last_level():
    assert resume_level(frozenset(_names(len(ordered_levels())))) == len(
        ordered_levels()
    )


@pytest.mark.parametrize("level", range(1, len(ordered_levels())))
def test_a_finished_level_is_not_run_again(level):
    assert resume_level(frozenset(_names(level))) == level


def test_a_paused_stage_sets_the_resume_level_to_its_own():
    done = _names(1)
    paused = next(spec.name for spec in ordered_levels()[1])
    rows = [_row(name, ScanActivityStatus.SUCCESS.value) for name in done]
    rows.append(_row(paused, ScanActivityStatus.PAUSED.value))

    assert resume_level(frozenset(stages_done(rows))) == 1


# ---------- the canvas epoch ----------


def test_a_task_from_the_current_canvas_runs():
    assert superseded(3, 3) is False


@pytest.mark.parametrize("task_epoch", [0, 1, 2])
def test_a_task_from_a_torn_down_canvas_is_refused(task_epoch):
    """A run_scan or stage task queued before a pause must not run beside the resumed canvas."""
    assert superseded(3, task_epoch) is True


def test_a_task_ahead_of_the_scan_is_refused():
    assert superseded(1, 2) is True


def test_a_legacy_row_with_no_epoch_reads_as_zero():
    assert superseded(None, 0) is False
    assert superseded(None, 1) is True


def test_a_task_that_carries_no_epoch_always_runs():
    """The reaper dispatches finalize without one, and it must still settle the scan."""
    assert superseded(0, None) is False
    assert superseded(7, None) is False
