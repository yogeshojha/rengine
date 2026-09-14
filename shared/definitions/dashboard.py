"""Windows and caps for the project dashboard."""

from __future__ import annotations

from datetime import timedelta
from enum import StrEnum


class DashboardWindow(StrEnum):
    WEEK = "7d"
    FORTNIGHT = "14d"
    MONTH = "30d"


WINDOW_DELTAS: dict[str, timedelta] = {
    DashboardWindow.WEEK.value: timedelta(days=7),
    DashboardWindow.FORTNIGHT.value: timedelta(days=14),
    DashboardWindow.MONTH.value: timedelta(days=30),
}
WINDOW_DAYS: dict[str, int] = {k: v.days for k, v in WINDOW_DELTAS.items()}
DEFAULT_WINDOW = DashboardWindow.WEEK.value

STALE_DAYS = 30
EXPIRING_DAYS = 30
SERIES_DAYS = 30
RUNS_PER_TARGET = 25
QUEUE_LIMIT = 40
CHANGES_LIMIT = 40
EXPOSURE_TOP = 8
DISCOVERY_LIMIT = 40
ITEMS_CAP = 100

EXPIRED_CERT_QUERY = "cert:expired and is:live"
EXPIRING_CERT_QUERY = "cert:expiring"


ACTIVITY_LIMIT = 40


class ActivityKind(StrEnum):
    RUN = "run"
    WATCH = "watch"
    PROGRAM = "program"
    FEEDS = "feeds"
    INTEL = "intel"
    CONNECTOR = "connector"


class QueueTier(StrEnum):
    ACT = "act"
    ATTEND = "attend"
    TRACK = "track"


TIER_ORDER: tuple[str, ...] = tuple(t.value for t in QueueTier)
TIER_LABELS: dict[str, str] = {
    QueueTier.ACT.value: "Act",
    QueueTier.ATTEND.value: "Attend",
    QueueTier.TRACK.value: "Track",
}
TIER_ACT_EPSS = 0.088
TIER_ATTEND_EPSS = 0.01


class FunnelStep(StrEnum):
    NAMES = "names"
    RESOLVED = "resolved"
    LIVE = "live"
    ORIGINS = "origins"
    FINDINGS = "findings"


FUNNEL_LABELS: dict[str, str] = {
    FunnelStep.NAMES.value: "Names found",
    FunnelStep.RESOLVED.value: "Resolve",
    FunnelStep.LIVE.value: "Answer HTTP",
    FunnelStep.ORIGINS.value: "Distinct origins",
    FunnelStep.FINDINGS.value: "With a finding",
}
FUNNEL_QUERIES: dict[str, str | None] = {
    FunnelStep.NAMES.value: "",
    FunnelStep.RESOLVED.value: "is:resolved",
    FunnelStep.LIVE.value: "is:live",
    FunnelStep.ORIGINS.value: None,
    FunnelStep.FINDINGS.value: "is:vulnerable",
}

# (key, label, lower bound in days, upper bound in days); None is open
CERT_BUCKETS: tuple[tuple[str, str, int | None, int | None], ...] = (
    ("expired", "Expired", None, 0),
    ("week", "Under 7 days", 0, 7),
    ("month", "Under 30 days", 7, 30),
    ("quarter", "Under 90 days", 30, 90),
    ("later", "Later", 90, None),
)


def cert_bucket_query(lower: int | None, upper: int | None) -> str:
    if upper == 0:
        return EXPIRED_CERT_QUERY
    parts = ["is:live", "not cert:expired"]
    if lower:
        parts.append(f"cert.expires:>={lower}d")
    if upper is not None:
        parts.append(f"cert.expires:<{upper}d")
    return " and ".join(parts)
