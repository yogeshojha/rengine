"""The abort check every tool in this worker process answers to."""

import contextlib
from collections.abc import Callable, Iterator


class StageAbortedError(Exception):
    """Raised when a stage detects the scan was cancelled or paused mid-run."""


_active: Callable[[], bool] | None = None


@contextlib.contextmanager
def aborting_on(check: Callable[[], bool] | None) -> Iterator[None]:
    """Bind one stage's abort check. A prefork child runs one task at a time."""
    global _active  # noqa: PLW0603
    previous = _active
    _active = check
    try:
        yield
    finally:
        _active = previous


def active_abort() -> Callable[[], bool] | None:
    return _active
