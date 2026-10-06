from __future__ import annotations

import pytest

from shared.definitions.activity import (
    cancelled_reason,
    issues_not_filed,
    run_cancelled,
    run_completed,
    run_failed,
    run_paused,
    targets_added,
)
from shared.definitions.notifications import ScanDeltas
from shared.enums.activity import ActivityLevel

pytestmark = pytest.mark.pipeline


def test_a_repeat_run_leads_with_its_worst_new_fact_then_its_growth():
    title, description, level = run_completed(
        {"subdomains_found": 1641},
        ScanDeltas(baseline=True, new_hosts=12, vulnerability_counts={"high": 3}),
        22140,
    )
    assert (title, description, level) == (
        "3 new high",
        "12 new web assets · 6h 9m",
        ActivityLevel.WARNING,
    )


def test_a_first_run_counts_everything_and_says_so():
    title, description, level = run_completed(
        {"subdomains_found": 12658},
        ScanDeltas(vulnerability_counts={"critical": 20, "high": 430}),
        27360,
    )
    assert title == "20 critical"
    assert description == "12,658 web assets · first run · 7h 36m"
    assert level == ActivityLevel.ERROR


def test_a_run_that_found_nothing_new_names_its_label():
    title, description, level = run_completed(
        {}, ScanDeltas(baseline=True), 300, "Tripwire · 3 web assets"
    )
    assert (title, description, level) == (
        "No changes",
        "Tripwire · 3 web assets · 5m",
        ActivityLevel.SUCCESS,
    )


def test_a_failure_names_its_stage_on_one_line():
    assert (
        run_failed("Subdomain Discovery", "The worker stopped twice.\n  Not run again.")
        == "Subdomain Discovery: The worker stopped twice. Not run again."
    )
    assert run_failed(None, None) == "One or more stages failed"


def test_a_cancel_names_who_and_what_was_kept():
    reason = cancelled_reason("rengine")
    assert reason == "Cancelled by rengine."
    assert (
        run_cancelled(reason, 240, {"subdomains_found": 658})
        == "Cancelled by rengine after 4m · 658 web assets kept"
    )
    assert run_cancelled(None, None, {}) == "Cancelled"


def test_pause_and_batches():
    assert run_paused(9, 21) == "9 of 21 stages done"
    assert targets_added(["a.io", "b.io", "c.io", "d.io"], "imported", skipped=1) == (
        "4 targets imported",
        "a.io, b.io, c.io and 1 more · 1 skipped",
    )
    assert issues_not_filed(["ThinkPHP RCE", "Zimbra upload"], "GitHub") == (
        "2 issues not filed",
        "GitHub · ThinkPHP RCE and 1 more",
    )
