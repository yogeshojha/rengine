"""Grouping hosts by how their screenshots render."""

from __future__ import annotations

from dataclasses import dataclass

from shared.definitions.correlation import (
    SCREENSHOT_DISTANCE,
    SCREENSHOT_MIN_POPCOUNT,
)
from shared.utils.imagehash import distance, hex_digest, popcount


@dataclass(frozen=True)
class RenderCluster:
    """Every row within `SCREENSHOT_DISTANCE` of one representative hash."""

    value: int
    count: int
    hashes: tuple[int, ...]

    @property
    def digest(self) -> str:
        return hex_digest(self.value)


def is_identity(value: int | None) -> bool:
    """Whether a hash carries enough structure to stand for a page."""
    if value is None:
        return False
    bits = popcount(value)
    return SCREENSHOT_MIN_POPCOUNT <= bits <= 64 - SCREENSHOT_MIN_POPCOUNT


def cluster(histogram: dict[int, int]) -> list[RenderCluster]:
    """Balls around the most populous hashes, counted the way the filter counts."""
    if not histogram:
        return []
    ranked = sorted(histogram, key=lambda h: (-histogram[h], h))
    claimed: set[int] = set()
    clusters: list[RenderCluster] = []
    for rep in ranked:
        if rep in claimed or not is_identity(rep):
            continue
        near = tuple(h for h in ranked if distance(rep, h) <= SCREENSHOT_DISTANCE)
        claimed.update(near)
        clusters.append(
            RenderCluster(
                value=rep,
                count=sum(histogram[h] for h in near),
                hashes=near,
            )
        )
    clusters.sort(key=lambda c: (-c.count, c.value))
    return clusters


def cluster_of(
    clusters: list[RenderCluster], value: int | None
) -> RenderCluster | None:
    """The cluster a row belongs to, preferring the largest that reaches it."""
    if value is None:
        return None
    for found in clusters:
        if value in found.hashes:
            return found
    return None
