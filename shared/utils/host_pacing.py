"""Adaptive per-host pacing: slow down a host that looks overloaded, ease back as it recovers."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager

CEILING = 2.0
BUMP = 0.06
EASE = 0.03
MAX_IN_FLIGHT = 12
_UNHEALTHY_STATUS = frozenset({429, 503})


class _State:
    __slots__ = ("backoff", "lock", "slots")

    def __init__(self, max_in_flight: int) -> None:
        self.backoff = 0.0
        self.lock = threading.Lock()
        self.slots = threading.BoundedSemaphore(max_in_flight)


class HostPacer:
    """One request pool paced per host. Healthy hosts run at full speed."""

    def __init__(
        self,
        *,
        ceiling: float = CEILING,
        bump: float = BUMP,
        ease: float = EASE,
        max_in_flight: int = MAX_IN_FLIGHT,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._ceiling = ceiling
        self._bump = bump
        self._ease = ease
        self._max_in_flight = max_in_flight
        self._sleep = sleep
        self._hosts: dict[str, _State] = {}
        self._guard = threading.Lock()

    def _state(self, host: str) -> _State:
        with self._guard:
            state = self._hosts.get(host)
            if state is None:
                state = _State(self._max_in_flight)
                self._hosts[host] = state
            return state

    def delay_for(self, host: str) -> float:
        state = self._state(host)
        with state.lock:
            return state.backoff

    def observe(
        self, host: str, *, status: int | None = None, transport_error: bool = False
    ) -> None:
        """Increase the backoff after an overloaded response, decrease after a clean one."""
        unhealthy = transport_error or (status in _UNHEALTHY_STATUS)
        state = self._state(host)
        with state.lock:
            if unhealthy:
                state.backoff = min(self._ceiling, state.backoff * 2 + self._bump)
            else:
                state.backoff = max(0.0, state.backoff - self._ease)

    @contextmanager
    def slot(self, host: str) -> Iterator[None]:
        """Hold one of the host's in-flight slots, after paying its current backoff."""
        if not host:
            yield
            return
        state = self._state(host)
        state.slots.acquire()
        try:
            delay = self.delay_for(host)
            if delay > 0:
                self._sleep(delay)
            yield
        finally:
            state.slots.release()


__all__ = ["HostPacer"]
