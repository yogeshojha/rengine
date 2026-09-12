from __future__ import annotations

import hashlib
from types import SimpleNamespace

import pytest

from shared.enums.target import TargetType
from shared.services.scan_resolve import ResolvedScanConfig
from stages.registry import execution_plan, stage_by_name
from stages.session_check.stage import SessionCheckStage, _Answer

pytestmark = pytest.mark.pipeline


def _answer(status: int, body: bytes = b"page") -> _Answer:
    return _Answer(status, hashlib.sha256(body).hexdigest(), len(body))


def _stage(
    answers: list[_Answer | None],
    target_value: str = "app.example.com",
    target_type: str = TargetType.DOMAIN.value,
    headers: dict | None = None,
    auth_names: list[str] | None = None,
) -> SessionCheckStage:
    resolved = ResolvedScanConfig(
        target_value=target_value,
        target_type=target_type,
        headers=headers if headers is not None else {"Authorization": "Bearer t"},
    )
    resolved._auth_header_names = (
        auth_names if auth_names is not None else ["Authorization"]
    )
    stage = SessionCheckStage.__new__(SessionCheckStage)
    stage.ctx = SimpleNamespace(
        target_value=target_value,
        target_type=target_type,
        resolved=resolved,
        is_aborted=None,
    )
    stage._cfg = SimpleNamespace(enabled=True, timeout=5)
    queue = list(answers)
    stage.sent = []

    def _get(_client, url, headers):
        stage.sent.append((url, dict(headers or {})))
        return queue.pop(0) if queue else None

    stage._get = _get
    stage._client = lambda: SimpleNamespace(close=lambda: None)
    stage.emit_progress = lambda _msg: None
    stage._check_abort = lambda: None
    return stage


@pytest.fixture(autouse=True)
def _cfg(monkeypatch):
    monkeypatch.setattr(
        SessionCheckStage, "cfg", property(lambda self: self._cfg), raising=False
    )


def test_a_session_that_changes_nothing_is_reported():
    same = _answer(200, b"<html>sign in</html>")
    result = _stage([same, same]).run()

    assert result.partial is True
    assert "nothing in this scan is authenticated" in result.warnings[0]


def test_credentials_the_target_refuses_are_reported():
    result = _stage([_answer(401), _answer(200)]).run()

    assert result.partial is True
    assert "wrong, expired or not accepted" in result.warnings[0]


def test_a_forbidden_answer_counts_as_refused():
    assert _stage([_answer(403), _answer(200)]).run().partial is True


def test_a_working_session_passes_quietly():
    result = _stage([_answer(200, b"dashboard"), _answer(302, b"login")]).run()

    assert result.partial is False
    assert result.warnings == []


def test_a_different_body_at_the_same_status_is_a_working_session():
    result = _stage([_answer(200, b"the real app"), _answer(200, b"sign in")]).run()
    assert result.partial is False


def test_a_target_that_does_not_answer_is_not_a_pass():
    result = _stage([None, None, None, None]).run()

    assert result.partial is True
    assert "could not be checked" in result.warnings[0]


def test_one_request_failing_decides_nothing():
    result = _stage([_answer(200), None, None, None]).run()

    assert result.partial is True
    assert "could not be checked" in result.warnings[0]


def test_a_target_with_no_url_says_so_rather_than_passing():
    result = _stage(
        [], target_value="203.0.113.0/24", target_type=TargetType.IP_RANGE.value
    ).run()

    assert result.partial is True
    assert "no URL to request" in result.warnings[0]


def test_the_second_scheme_is_tried_before_giving_up():
    result = _stage([None, _answer(200, b"a"), _answer(200, b"b")]).run()
    assert result.partial is False


def test_it_does_not_run_without_credentials():
    stage = _stage([], headers={}, auth_names=[])
    assert stage.should_run() is False


def test_it_runs_when_the_context_carries_credentials():
    assert _stage([]).should_run() is True


def test_an_extra_header_is_not_a_credential():
    stage = _stage([], headers={"X-Scan": "rengine"}, auth_names=[])
    assert stage.should_run() is False


def test_the_control_request_is_actually_sent_without_the_credentials():
    stage = _stage(
        [_answer(200, b"app"), _answer(200, b"login")],
        headers={"Authorization": "Bearer t", "X-Scan": "rengine"},
        auth_names=["Authorization"],
    )
    stage.run()

    (_url, signed), (_url2, bare) = stage.sent[0], stage.sent[1]
    assert signed["Authorization"] == "Bearer t"
    assert "Authorization" not in bare, "the control must not carry the credentials"
    assert bare["X-Scan"] == "rengine", "and must keep everything else"


def test_both_requests_go_to_the_same_url():
    stage = _stage([_answer(200, b"a"), _answer(200, b"b")])
    stage.run()
    assert stage.sent[0][0] == stage.sent[1][0]


def test_the_control_request_drops_exactly_the_credentials():
    resolved = ResolvedScanConfig(
        target_value="a.example.com",
        target_type=TargetType.DOMAIN.value,
        headers={"Authorization": "Bearer t", "X-Scan": "rengine"},
    )
    resolved._auth_header_names = ["Authorization"]

    assert resolved.auth_headers() == {"Authorization": "Bearer t"}
    assert resolved.headers_without_auth() == {"X-Scan": "rengine"}


def test_it_runs_before_anything_expensive():
    plan = execution_plan()
    step = next(i for i, s in enumerate(plan) if "session_check" in s)
    spend = next(i for i, s in enumerate(plan) if "url_discovery" in s)

    assert step < spend
    assert step <= 1


def test_it_declares_that_it_may_not_be_deferred():
    spec = stage_by_name()["session_check"]
    assert spec.deferrable is False
    assert spec.touches_target is True, "without this the deferral rule never sees it"


def test_a_stage_may_be_deferred_by_default():
    assert stage_by_name()["waf_detect"].deferrable is True
