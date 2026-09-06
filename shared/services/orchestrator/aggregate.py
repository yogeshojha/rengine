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
# every headline is measured from its table: several stages write the same rows, so
# summing per-stage results both double-counts and misses the stages that report no key.
DERIVED_COUNTS: dict[str, str] = {
    "subdomains_found": "SELECT count(*) FROM subdomains WHERE scan_id = :sid",
    "ips_found": "SELECT count(*) FROM ip_addresses WHERE scan_id = :sid",
    "open_ports_found": "SELECT count(*) FROM ports WHERE scan_id = :sid",
    "http_assets_found": "SELECT count(*) FROM http_assets WHERE scan_id = :sid",
    "endpoints_found": "SELECT count(*) FROM endpoints WHERE scan_id = :sid",
    "vulnerabilities_found": "SELECT count(*) FROM vulnerabilities WHERE scan_id = :sid",
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
