from __future__ import annotations

import pytest

from stages.vulnerability_scan import stage as vuln_stage
from stages.vulnerability_scan.stage import VulnerabilityScanStage

pytestmark = pytest.mark.pipeline


class _Stage:
    session = object()

    def __init__(self) -> None:
        self.progress: list[str] = []
        self.polls = 0

    def emit_progress(self, message: str) -> None:
        self.progress.append(message)

    def _check_abort(self) -> None:
        self.polls += 1


def _patch(monkeypatch, *, ready, loads):
    ready, loads = iter(ready), iter(loads)

    def load(_session):
        value = next(loads)
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr(vuln_stage, "library_ready", lambda _s: next(ready))
    monkeypatch.setattr(vuln_stage, "sync_official", load)
    monkeypatch.setattr(vuln_stage.time, "sleep", lambda _s: None)


def test_an_empty_library_is_downloaded_in_the_stage(monkeypatch):
    _patch(monkeypatch, ready=[False], loads=[12852])
    stage = _Stage()

    VulnerabilityScanStage._ensure_library(stage)

    assert stage.progress == ["downloading the check library", "12852 checks indexed"]


def test_a_load_running_elsewhere_is_waited_for(monkeypatch):
    _patch(monkeypatch, ready=[False, False, True], loads=[None, None])
    stage = _Stage()

    VulnerabilityScanStage._ensure_library(stage)

    assert stage.polls == 1


def test_a_failed_download_fails_the_stage(monkeypatch):
    _patch(monkeypatch, ready=[False], loads=[OSError("no route to host")])

    with pytest.raises(RuntimeError, match="could not be downloaded: no route to host"):
        VulnerabilityScanStage._ensure_library(_Stage())


def test_a_load_that_never_lands_stops_at_the_wait(monkeypatch):
    _patch(monkeypatch, ready=[False, False], loads=[None])
    monkeypatch.setattr(vuln_stage, "LIBRARY_WAIT_SECONDS", -1)

    with pytest.raises(RuntimeError, match="did not finish"):
        VulnerabilityScanStage._ensure_library(_Stage())
