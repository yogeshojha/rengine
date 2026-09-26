"""Tool args add flags; they never restate one the stage set."""

from __future__ import annotations

import pytest

from tools.ffuf.client import FFUF_ALIASES
from tools.nuclei.client import NUCLEI_ALIASES
from tools.runner.executor import merge_extra_args

pytestmark = pytest.mark.pipeline


def test_a_restated_flag_and_its_value_are_dropped():
    stage = ["-rate-limit", "5", "-threads", "20"]
    extra = ["-rate-limit", "9999", "-retries", "3"]
    assert merge_extra_args(stage, extra) == ["-retries", "3"]


def test_the_equals_spelling_is_dropped_too():
    assert merge_extra_args(["-timeout", "10"], ["-timeout=99", "-silent"]) == [
        "-silent"
    ]


def test_reserved_flags_are_dropped_before_the_runner_adds_them():
    extra = ["-l", "/etc/passwd", "-json", "-o", "elsewhere.txt", "-stats"]
    assert merge_extra_args([], extra, ("-l", "-json", "-o")) == ["-stats"]


def test_a_boolean_flag_does_not_swallow_the_next_flag():
    assert merge_extra_args(["-silent"], ["-silent", "-stats"]) == ["-stats"]


def test_unrelated_flags_pass_through_in_order():
    extra = ["-stats", "-si", "5", "-tags", "cve"]
    assert merge_extra_args(["-rate-limit", "5"], extra) == extra


def test_a_short_spelling_cannot_restate_a_long_flag():
    stage = ["-rate-limit", "150", "-list", "/run/gen.txt", "-max-host-error", "30"]
    extra = ["-rl", "9999", "-l", "/run/mine.txt", "-mhe", "0", "-j", "-stats"]
    assert merge_extra_args(stage, extra, ("-list", "-jsonl"), NUCLEI_ALIASES) == [
        "-stats"
    ]


def test_the_reserved_set_covers_the_short_spelling_too():
    assert merge_extra_args(
        [], ["-l", "x", "-o", "y", "-tags", "cve"], ("-list", "-output"), NUCLEI_ALIASES
    ) == ["-tags", "cve"]


def test_ffuf_folds_a_custom_silent_into_its_own_short_flag():
    """ffuf has no `-silent`; passed through, it would fail the run."""
    extra = ["-silent", "-s", "-ac"]
    assert merge_extra_args([], extra, ("-s",), FFUF_ALIASES) == ["-ac"]
