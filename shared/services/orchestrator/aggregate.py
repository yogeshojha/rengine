import uuid
from collections.abc import Iterable
from typing import TYPE_CHECKING

from sqlalchemy import text

from shared.enums.scan import (
    ACTIVITY_TERMINAL_STATUSES,
    ScanActivityStatus,
    ScanStatus,
)
from shared.models.scan_activity import ScanActivity

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# rollup SSOT — a new headline metric needs an entry here + a scans column (migration)
# + shared.definitions.notifications._SCAN_COUNT_LABELS; other count keys stay stage-only.
COUNT_TO_COLUMN = {
    "subdomains": "subdomains_found",
    "ips": "ips_found",
    "open_ports": "open_ports_found",
    "http_assets": "http_assets_found",
    "vulnerabilities": "vulnerabilities_found",
    "endpoints": "endpoints_found",
}


# counts several stages write into the same rows; summing their results double-counts,
# so these are measured from the table instead
DERIVED_COUNTS: dict[str, str] = {
    "open_ports_found": "SELECT count(*) FROM ports WHERE scan_id = :sid",
}


def derived_counts(session: "Session", scan_id: uuid.UUID) -> dict[str, int]:
    return {
        column: int(session.execute(text(sql).bindparams(sid=scan_id)).scalar() or 0)
        for column, sql in DERIVED_COUNTS.items()
    }


def aggregate_status(activities: Iterable[ScanActivity]) -> str:
    # in-flight/empty -> RUNNING sentinel (don't finalize); any failed stage -> failed
    statuses = [a.status for a in activities]
    if not statuses:
        return ScanStatus.RUNNING.value
    if any(s not in ACTIVITY_TERMINAL_STATUSES for s in statuses):
        return ScanStatus.RUNNING.value
    if any(s == ScanActivityStatus.ABORTED.value for s in statuses):
        return ScanStatus.CANCELLED.value
    if any(s == ScanActivityStatus.FAILED.value for s in statuses):
        return ScanStatus.FAILED.value
    return ScanStatus.COMPLETED.value


def aggregate_counts(activities: Iterable[ScanActivity]) -> dict[str, int]:
    """Sum per-stage result counts into the scan rollup columns."""
    totals: dict[str, int] = dict.fromkeys(COUNT_TO_COLUMN.values(), 0)
    for activity in activities:
        for key, column in COUNT_TO_COLUMN.items():
            value = (activity.result or {}).get(key)
            if isinstance(value, int):
                totals[column] += value
    return totals
