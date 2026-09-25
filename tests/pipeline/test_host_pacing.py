from __future__ import annotations

import threading

import pytest

from shared.utils.host_pacing import CEILING, HostPacer

pytestmark = pytest.mark.pipeline


def test_a_healthy_host_carries_no_delay() -> None:
    pacer = HostPacer()
    pacer.observe("h", status=200)
    assert pacer.delay_for("h") == 0.0


def test_an_overloaded_host_backs_off_multiplicatively() -> None:
    pacer = HostPacer()
    pacer.observe("h", status=429)
    first = pacer.delay_for("h")
    pacer.observe("h", status=503)
    second = pacer.delay_for("h")
    assert first > 0
    assert second > first * 2


def test_a_transport_error_counts_as_unhealthy() -> None:
    pacer = HostPacer()
    pacer.observe("h", transport_error=True)
    assert pacer.delay_for("h") > 0


def test_the_backoff_is_capped() -> None:
    pacer = HostPacer()
    for _ in range(50):
        pacer.observe("h", status=503)
    assert pacer.delay_for("h") == CEILING


def test_recovery_eases_the_backoff_down() -> None:
    pacer = HostPacer(ease=0.1)
    for _ in range(3):
        pacer.observe("h", status=503)
    high = pacer.delay_for("h")
    pacer.observe("h", status=200)
    assert 0 <= pacer.delay_for("h") < high


def test_hosts_are_paced_independently() -> None:
    pacer = HostPacer()
    pacer.observe("a", status=503)
    assert pacer.delay_for("a") > 0
    assert pacer.delay_for("b") == 0.0


def test_the_slot_pays_the_backoff_before_yielding() -> None:
    slept: list[float] = []
    pacer = HostPacer(sleep=slept.append)
    pacer.observe("h", status=503)
    with pacer.slot("h"):
        pass
    assert slept == [pacer.delay_for("h")]


def test_the_slot_bounds_concurrency_per_host() -> None:
    pacer = HostPacer(max_in_flight=2, sleep=lambda _d: None)
    held = threading.Semaphore(0)
    release = threading.Event()
    running = []

    def worker():
        with pacer.slot("h"):
            running.append(1)
            held.release()
            release.wait(1)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    held.acquire()
    held.acquire()
    # both slots are held
    assert sum(running) == 2
    release.set()
    for thread in threads:
        thread.join()


def test_an_empty_host_is_a_no_op() -> None:
    pacer = HostPacer(sleep=lambda _d: pytest.fail("should not sleep"))
    with pacer.slot(""):
        pass
