"""Who is scanned first when the budget runs out. Never alphabetical."""

from __future__ import annotations

from shared.services.scan_surface.cluster import RootCandidate

_STATUS_SCORE: tuple[tuple[range, float], ...] = (
    (range(200, 400), 40.0),
    (range(401, 404), 30.0),
    (range(404, 405), 15.0),
    (range(500, 600), 5.0),
)
_UNCOVERED_BONUS = 25.0
_MEMBER_BONUS = 2.0
_MAX_MEMBER_BONUS = 40.0
_ENDPOINT_BONUS = 15.0
_TAG_BONUS = 3.0
_DIRECT_BONUS = 10.0
_DEPTH_BONUS = 10.0


def _status_score(status: int | None) -> float:
    if status is None:
        return 0.0
    for span, score in _STATUS_SCORE:
        if status in span:
            return score
    return 20.0


def base_rank(candidate: RootCandidate) -> float:
    """The score before the cluster is known."""
    score = _status_score(candidate.status)
    if not candidate.covered_before:
        score += _UNCOVERED_BONUS
    score += _ENDPOINT_BONUS * min(candidate.endpoints, 50) / 50
    score += _TAG_BONUS * min(len(candidate.tags), 5)
    if not candidate.is_cdn:
        score += _DIRECT_BONUS
    labels = candidate.host.count(".") + 1
    score += max(0.0, _DEPTH_BONUS - max(0, labels - 2) * 2)
    return round(score, 3)


def cluster_rank(base: float, members: int) -> float:
    """A representative standing for many is worth more."""
    return round(base + min(_MAX_MEMBER_BONUS, _MEMBER_BONUS * max(0, members - 1)), 3)


__all__ = ["base_rank", "cluster_rank"]
