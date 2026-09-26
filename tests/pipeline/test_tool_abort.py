from __future__ import annotations

import os
import subprocess
import tempfile
import time
from pathlib import Path

import pytest

from tools.runner.abort import StageAbortedError, aborting_on
from tools.runner.executor import CLIToolRunner, _run_process
from tools.runner.models import ToolFlags, ToolResult

pytestmark = pytest.mark.pipeline

_SH = "/bin/sh"


def _run(script: str, **over):
    options = {
        "stdin_data": None,
        "env": dict(os.environ),
        "cwd": "/tmp",  # noqa: S108
        "timeout": 30,
        "should_stop": None,
    }
    options.update(over)
    return _run_process([_SH, "-c", script], **options)


def test_a_finished_tool_returns_without_waiting_for_the_poll():
    started = time.monotonic()
    done = _run("echo out; echo err >&2")
    assert done.returncode == 0
    assert done.stdout.strip() == "out"
    assert done.stderr.strip() == "err"
    assert time.monotonic() - started < 1.0


def test_stdin_reaches_the_tool():
    done = _run("cat", stdin_data="one\ntwo\n")
    assert done.stdout == "one\ntwo\n"


def test_a_failing_tool_keeps_its_exit_code():
    assert _run("exit 3").returncode == 3


def test_a_tool_past_its_budget_times_out():
    with pytest.raises(subprocess.TimeoutExpired):
        _run("sleep 30", timeout=1)


def test_a_halted_scan_stops_the_tool():
    started = time.monotonic()
    with pytest.raises(StageAbortedError):
        _run("sleep 60", should_stop=lambda: True)
    assert time.monotonic() - started < 8.0


def _sh(script: str) -> ToolResult:
    """A blocking run through the public entry point, which binds the abort check."""
    return CLIToolRunner("sh").run(
        args=["-c", script], use_output_file=False, silent=False
    )


def test_a_stage_that_binds_an_abort_check_stops_the_blocking_path():
    with aborting_on(lambda: True), pytest.raises(StageAbortedError):
        _sh("sleep 60")


def test_a_tool_runs_to_the_end_while_the_scan_is_healthy():
    with aborting_on(lambda: False):
        assert _sh("echo alive").stdout.strip() == "alive"


def test_no_bound_check_leaves_the_blocking_path_alone():
    assert _sh("echo alive").stdout.strip() == "alive"


def test_a_grandchild_does_not_outlive_the_stop():
    marker = Path(tempfile.mkdtemp()) / "alive"
    script = f"(sleep 3; touch {marker}) & sleep 60"
    with pytest.raises(StageAbortedError):
        _run(script, should_stop=lambda: True)
    time.sleep(5)
    assert not marker.exists()


def _stream(script: str, **over):
    """A streaming run through the public entry point."""
    # the json flag is already in args, so nothing is appended to the command
    runner = CLIToolRunner("sh", flags=ToolFlags(json="-c"))
    options = {"args": ["-c", script], "silent": False}
    options.update(over)
    with runner.stream_json(**options) as outcome:
        list(outcome.records)
    return outcome


def test_a_halted_scan_stops_a_streaming_tool():
    started = time.monotonic()
    with aborting_on(lambda: True):
        outcome = _stream('echo "{}"; sleep 60')
    assert outcome.stopped is True
    assert outcome.ok is False, "a stopped stream is not a successful one"
    assert outcome.timed_out is False, "halted is not timed out"
    assert time.monotonic() - started < 20.0


def test_a_streaming_tool_runs_to_the_end_while_the_scan_is_healthy():
    with aborting_on(lambda: False):
        outcome = _stream('echo "{\\"a\\": 1}"')
    assert outcome.stopped is False
    assert outcome.ok is True
    assert outcome.record_count == 1
