"""The crawl budget the form states is the budget the runner enforces."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from tools.katana.client import _KILL_SLACK_SECONDS, KatanaClient

pytestmark = pytest.mark.pipeline


def _kill_after(minutes: int) -> int:
    return KatanaClient.kill_after(SimpleNamespace(max_duration_minutes=minutes))


def test_a_long_budget_is_not_cut_at_the_runner_default():
    assert _kill_after(120) == 120 * 60 + _KILL_SLACK_SECONDS


def test_no_limit_means_no_kill_timer():
    assert _kill_after(0) == 0


def test_the_kill_timer_sits_after_katanas_own_deadline():
    assert _kill_after(5) > 5 * 60
