"""Incremental result writing: a stage commits what it has while its tool is still running."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable

DEFAULT_ROWS = 500
DEFAULT_SECONDS = 2.0
ANNOUNCE_SECONDS = 2.0


class ResultSink[T]:
    """Buffers rows, writes and commits them on a size or age trigger, then announces."""

    def __init__(
        self,
        write: Callable[[list[T]], int],
        *,
        announce: Callable[[int], None] | None = None,
        rows: int = DEFAULT_ROWS,
        seconds: float = DEFAULT_SECONDS,
        announce_seconds: float = ANNOUNCE_SECONDS,
    ) -> None:
        self._write = write
        self._announce = announce
        self._rows = max(1, rows)
        self._seconds = max(0.0, seconds)
        self._announce_seconds = max(0.0, announce_seconds)
        self._buffer: list[T] = []
        self._last_flush = time.monotonic()
        self._last_announce = 0.0
        self._unannounced = 0
        self.written = 0
        self.flushes = 0

    @property
    def pending(self) -> int:
        return len(self._buffer)

    def add(self, item: T) -> None:
        self._buffer.append(item)
        if self._due():
            self.flush()

    def extend(self, items: Iterable[T]) -> None:
        for item in items:
            self.add(item)

    def tick(self) -> int:
        """Flush because the age bound was reached."""
        return self.flush() if self._due() else 0

    def flush(self, *, final: bool = False) -> int:
        if not self._buffer:
            self._last_flush = time.monotonic()
            if final:
                self._say(force=True)
            return 0
        batch, self._buffer = self._buffer, []
        self._last_flush = time.monotonic()
        written = int(self._write(batch) or 0)
        self.written += written
        self._unannounced += written
        self.flushes += 1
        self._say(force=final)
        return written

    def close(self) -> int:
        return self.flush(final=True)

    def _due(self) -> bool:
        if len(self._buffer) >= self._rows:
            return True
        return (
            bool(self._buffer) and time.monotonic() - self._last_flush >= self._seconds
        )

    def _say(self, *, force: bool) -> None:
        if self._announce is None or not self._unannounced:
            return
        now = time.monotonic()
        if not force and now - self._last_announce < self._announce_seconds:
            return
        self._last_announce = now
        count, self._unannounced = self._unannounced, 0
        self._announce(count)


__all__ = ["ResultSink"]
