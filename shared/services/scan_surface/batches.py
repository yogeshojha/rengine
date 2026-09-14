"""Batches: the unit of coverage. The time cut lands between them, never inside a host."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from shared.definitions.scan_surface import (
    BATCH_MAX_HOSTS,
    BATCH_MIN_HOSTS,
    BATCH_SECONDS,
)


def batch_size(cost_per_host: int, rate: int, seconds: int = BATCH_SECONDS) -> int:
    """Hosts one invocation can sweep in about `seconds` at `rate`."""
    budget = max(1, rate) * max(1, seconds)
    size = budget // max(1, cost_per_host)
    return max(BATCH_MIN_HOSTS, min(BATCH_MAX_HOSTS, size))


def chunk[T](items: Sequence[T], size: int) -> list[list[T]]:
    size = max(1, size)
    return [list(items[i : i + size]) for i in range(0, len(items), size)]


def batches[T](items: Iterable[T], cost_per_host: int, rate: int) -> list[list[T]]:
    return chunk(list(items), batch_size(cost_per_host, rate))


__all__ = ["batch_size", "batches", "chunk"]
