import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.services import readiness

CALLERS = 8


@pytest.fixture
def inspected(monkeypatch):
    calls: list[float] = []
    answer = {"value": (True, 4)}
    gate = threading.Lock()

    def slow_inspect():
        with gate:
            calls.append(time.monotonic())
        time.sleep(0.3)
        return answer["value"]

    monkeypatch.setattr(readiness, "_inspect", slow_inspect)
    monkeypatch.setattr(readiness, "_last", {})
    return calls, answer


def _ask_together() -> list[tuple[bool, int | None]]:
    with ThreadPoolExecutor(max_workers=CALLERS) as pool:
        return list(pool.map(lambda _: readiness._workers(), range(CALLERS)))


def test_concurrent_callers_share_one_inspect(inspected):
    calls, _ = inspected
    assert _ask_together() == [(True, 4)] * CALLERS
    assert len(calls) == 1


def test_an_offline_answer_is_shared_by_the_callers_waiting_on_it(inspected):
    calls, answer = inspected
    answer["value"] = (False, None)
    assert _ask_together() == [(False, None)] * CALLERS
    assert len(calls) == 1


def test_an_offline_answer_is_asked_again_on_the_next_call(inspected):
    calls, answer = inspected
    answer["value"] = (False, None)
    readiness._workers()
    answer["value"] = (True, 2)
    assert readiness._workers() == (True, 2)
    assert len(calls) == 2


def test_an_online_answer_is_held(inspected):
    calls, _ = inspected
    readiness._workers()
    readiness._workers()
    assert len(calls) == 1


def test_a_caller_during_a_refresh_gets_the_last_answer(inspected, monkeypatch):
    calls, answer = inspected
    expired = time.monotonic() - readiness.ONLINE_TTL_SECONDS - 1
    monkeypatch.setattr(readiness, "_last", {"workers": (expired, True, 3)})
    answer["value"] = (False, None)
    with ThreadPoolExecutor(max_workers=2) as pool:
        refresh = pool.submit(readiness._workers)
        time.sleep(0.1)
        t0 = time.monotonic()
        assert readiness._workers() == (True, 3)
        assert time.monotonic() - t0 < 0.1
        assert refresh.result() == (False, None)
    assert len(calls) == 1
