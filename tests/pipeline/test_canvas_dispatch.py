from __future__ import annotations

from typing import Any

import pytest

import shared.services.celery_dispatch as dispatch
from shared.services.orchestrator import superseded

pytestmark = pytest.mark.pipeline


class _Client:
    def __init__(self) -> None:
        self.sent: list[tuple[str, dict[str, Any]]] = []

    def send_task(self, name: str, *, kwargs: dict[str, Any], queue: str) -> None:  # noqa: ARG002
        self.sent.append((name, kwargs))


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> _Client:
    stub = _Client()
    monkeypatch.setattr(dispatch, "get_celery_client", lambda: stub)
    return stub


def test_a_launch_names_the_canvas_it_was_queued_for(client: _Client):
    dispatch.dispatch_scan_run("s1", 0)
    assert client.sent == [("app.tasks.scan.run_scan", {"scan_id": "s1", "epoch": 0})]


def test_a_resume_names_the_canvas_it_was_queued_for(client: _Client):
    dispatch.dispatch_scan_resume("s1", 3)
    assert client.sent == [
        ("app.tasks.scan.resume_scan", {"scan_id": "s1", "epoch": 3})
    ]


def test_a_launch_queued_before_a_resume_is_refused_by_its_epoch(client: _Client):
    dispatch.dispatch_scan_run("s1", 0)
    _, queued = client.sent[0]
    assert superseded(1, queued["epoch"])


def test_a_launch_from_the_current_canvas_runs(client: _Client):
    dispatch.dispatch_scan_run("s1", 2)
    _, queued = client.sent[0]
    assert not superseded(2, queued["epoch"])


def test_finalize_carries_no_epoch_so_the_reaper_can_settle_any_canvas(client: _Client):
    dispatch.dispatch_scan_finalize("s1")
    _, queued = client.sent[0]
    assert "epoch" not in queued
    assert not superseded(7, queued.get("epoch"))
