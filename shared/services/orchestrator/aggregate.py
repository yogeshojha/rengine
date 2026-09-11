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

DERIVED_COUNTS: dict[str, str] = {
    "subdomains_found": "SELECT count(*) FROM subdomains WHERE scan_id = :sid",
    "ips_found": "SELECT count(*) FROM ip_addresses WHERE scan_id = :sid",
    "open_ports_found": "SELECT count(*) FROM ports WHERE scan_id = :sid",
    "http_assets_found": "SELECT count(*) FROM http_assets WHERE scan_id = :sid",
    "endpoints_found": "SELECT count(*) FROM endpoints WHERE scan_id = :sid",
    "vulnerabilities_found": "SELECT count(*) FROM vulnerabilities WHERE scan_id = :sid",
}


def derived_counts(
    session: "Session", scan_id: uuid.UUID, columns: Iterable[str] | None = None
) -> dict[str, int]:
    wanted = set(columns) if columns is not None else None
    return {
        column: int(session.execute(text(sql).bindparams(sid=scan_id)).scalar() or 0)
        for column, sql in DERIVED_COUNTS.items()
        if wanted is None or column in wanted
    }


def aggregate_status(activities: Iterable[ScanActivity]) -> str:
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
