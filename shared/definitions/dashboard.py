"""Windows and caps for the project dashboard."""

from __future__ import annotations

from datetime import timedelta
from enum import StrEnum


class DashboardWindow(StrEnum):
    DAY = "24h"
    WEEK = "7d"
    MONTH = "30d"


WINDOW_DELTAS: dict[str, timedelta] = {
    DashboardWindow.DAY.value: timedelta(days=1),
    DashboardWindow.WEEK.value: timedelta(days=7),
    DashboardWindow.MONTH.value: timedelta(days=30),
}
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
