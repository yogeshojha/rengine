"""Aggregate stage outcomes into the final scan status + terminal notification/event."""

from sqlalchemy import Integer, String, bindparam, select, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Session

from shared.definitions.notifications import (
    ScanDeltas,
    scan_count_summary,
    scan_digest,
    scan_failed,
)
from shared.definitions.ports import SENSITIVE_PORTS
from shared.definitions.vulnerabilities import SUPPRESSED_STATES, CoverageStatus
from shared.enums.activity import ActivityEvent, ActivityLevel
from shared.enums.scan import SCAN_TERMINAL_STATUSES, ScanScope, ScanStatus
from shared.logging import get_logger
from shared.models.scan import Scan
from shared.models.scan_activity import ScanActivity
from shared.models.vulnerability import VulnerabilityCoverage
from shared.services.activity_log import ActivityLogService
from shared.services.celery_dispatch import dispatch_interest_evaluation
from shared.services.notification_sync import SyncNotificationPublisher
from shared.services.orchestrator import (
    aggregate_status,
    derived_counts,
)
from shared.services.orchestrator.events import ScanEventPublisher
from shared.services.recheck import compute_rechecks
from shared.utils.datetime import utc_now
from stages.registry import ordered_levels

logger = get_logger(__name__)


def _undispatched(activities: list[ScanActivity]) -> str | None:
    """Report the stages the canvas never reached, so a truncated run is never 'completed'."""
    expected = sum(len(level) for level in ordered_levels())
    if len(activities) >= expected:
        return None
    return (
        f"The scan stopped after {len(activities)} of {expected} stages. "
        "The remaining stages were never dispatched."
    )


def _notify(
    notifier: SyncNotificationPublisher,
    session: Session,
    scan: Scan,
    payload: dict | None,
) -> None:
    if payload is None:
        return
    try:
        notifier.publish(
            session=session,
            type=payload["type"],
            severity=payload["severity"],
            title=payload["title"],
            message=payload["message"],
            metadata=payload.get("metadata"),
            project_id=scan.project_id,
        )
    except Exception:
        logger.warning("scan notification dispatch failed", exc_info=True)


def _finalize_user_cancelled(
    session: Session, scan: Scan, events: ScanEventPublisher
) -> None:
    if scan.completed_at is None:
        scan.completed_at = utc_now()
        session.add(scan)
        session.commit()
        _log_cancelled(ActivityLogService(session), scan)
        session.commit()
    events.scan_cancelled(status=scan.status)


def _log_cancelled(activity_log: ActivityLogService, scan: Scan) -> None:
    target_value = (scan.execution_config or {}).get("target_value", "")
    activity_log.log(
        event=ActivityEvent.SCAN_CANCELLED,
        title=f"Scan cancelled · {target_value}",
        description=scan.engine_name,
        level=ActivityLevel.WARNING,
        project_id=scan.project_id,
        target_id=scan.target_id,
        scan_id=scan.id,
        target_value=target_value,
    )


# an earlier census run of this target; a focused rescan is never a baseline
_HOST_BASELINE_SQL = """
SELECT EXISTS (
    SELECT 1 FROM subdomains b
    JOIN scans bs ON bs.id = b.scan_id AND bs.scope = 'full'
                 AND bs.id <> :sid AND bs.started_at < :started
    WHERE b.target_id = :tid
)
"""

_SERVICE_BASELINE_SQL = """
SELECT EXISTS (
    SELECT 1 FROM ports b
    JOIN scans bs ON bs.id = b.scan_id AND bs.scope = 'full'
                 AND bs.id <> :sid AND bs.started_at < :started
    WHERE b.target_id = :tid
)
"""

_VULN_BASELINE_SQL = """
SELECT EXISTS (
    SELECT 1 FROM vulnerabilities b
    JOIN scans bs ON bs.id = b.scan_id AND bs.scope = 'full'
                 AND bs.id <> :sid AND bs.started_at < :started
    WHERE b.target_id = :tid
)
"""

_NEW_SUBDOMAINS_SQL = """
WITH seen AS (
    SELECT DISTINCT b.name FROM subdomains b
    JOIN scans bs ON bs.id = b.scan_id AND bs.scope = 'full'
                 AND bs.id <> :sid AND bs.started_at < :started
    WHERE b.target_id = :tid
)
SELECT count(*) AS total
FROM subdomains p
WHERE p.scan_id = :sid
  AND NOT EXISTS (SELECT 1 FROM seen s WHERE s.name = p.name)
"""

_NEW_SERVICES_SQL = """
WITH seen AS (
    SELECT DISTINCT b.ip, b.number FROM ports b
    JOIN scans bs ON bs.id = b.scan_id AND bs.scope = 'full'
                 AND bs.id <> :sid AND bs.started_at < :started
    WHERE b.target_id = :tid
)
SELECT count(*) AS total,
       count(*) FILTER (WHERE p.number = ANY(:sensitive_ports)) AS sensitive
FROM ports p
WHERE p.scan_id = :sid
  AND NOT EXISTS (
      SELECT 1 FROM seen s WHERE s.ip = p.ip AND s.number = p.number
  )
"""

_NEW_VULNS_SQL = """
WITH seen AS (
    SELECT DISTINCT b.fingerprint FROM vulnerabilities b
    JOIN scans bs ON bs.id = b.scan_id AND bs.scope = 'full'
                 AND bs.id <> :sid AND bs.started_at < :started
    WHERE b.target_id = :tid
)
SELECT v.severity AS severity,
       count(*) AS total,
       count(*) FILTER (WHERE v.is_kev) AS kev
FROM vulnerabilities v
WHERE v.scan_id = :sid
  AND NOT EXISTS (
      SELECT 1 FROM vulnerability_triage t
      WHERE t.target_id = v.target_id AND t.fingerprint = v.fingerprint
        AND t.state = ANY(:suppressed)
  )
  AND NOT EXISTS (SELECT 1 FROM seen s WHERE s.fingerprint = v.fingerprint)
GROUP BY v.severity
"""


def _has_baseline(session: Session, scan: Scan, sql: str) -> bool:
    return bool(session.execute(text(sql).bindparams(*_scope(scan))).scalar_one())


def _scope(scan: Scan) -> list:
    return [
        bindparam("sid", scan.id),
        bindparam("tid", scan.target_id),
        bindparam("started", scan.started_at or utc_now()),
    ]


def _count_new_subdomains(session: Session, scan: Scan) -> int:
    return int(
        session.execute(
            text(_NEW_SUBDOMAINS_SQL).bindparams(*_scope(scan))
        ).scalar_one()
        or 0
    )


def _count_new_services(session: Session, scan: Scan) -> tuple[int, int]:
    row = session.execute(
        text(_NEW_SERVICES_SQL).bindparams(
            *_scope(scan),
            bindparam("sensitive_ports", SENSITIVE_PORTS, type_=ARRAY(Integer)),
        )
    ).one()
    return int(row.total or 0), int(row.sensitive or 0)


def _count_new_vulnerabilities(session: Session, scan: Scan) -> tuple[dict, int, int]:
    rows = session.execute(
        text(_NEW_VULNS_SQL).bindparams(
            *_scope(scan),
            bindparam("suppressed", list(SUPPRESSED_STATES), type_=ARRAY(String)),
        )
    ).all()
    counts = {row.severity: int(row.total) for row in rows}
    kev = sum(int(row.kev or 0) for row in rows)
    return counts, kev, sum(counts.values())


def _dropped_hosts(session: Session, scan: Scan) -> int:
    rows = (
        session.execute(
            select(VulnerabilityCoverage.hosts_dropped).where(
                VulnerabilityCoverage.scan_id == scan.id,
                VulnerabilityCoverage.status == CoverageStatus.PARTIAL.value,
            )
        )
        .scalars()
        .all()
    )
    return sum(len(entry or []) for entry in rows)


def _dispatch_interest(scan: Scan) -> None:
    try:
        dispatch_interest_evaluation(str(scan.id))
    except Exception:
        logger.warning("interest dispatch failed", exc_info=True)


def _guard(fn, fallback):
    try:
        return fn()
    except Exception:
        logger.warning("scan delta measurement failed", exc_info=True)
        return fallback


def _measure(session: Session, scan: Scan) -> ScanDeltas:
    """Each dimension is only compared where an earlier census run covered it."""
    hosts, services, vulns = (
        _guard(lambda sql=sql: _has_baseline(session, scan, sql), False)
        for sql in (_HOST_BASELINE_SQL, _SERVICE_BASELINE_SQL, _VULN_BASELINE_SQL)
    )
    new_services, sensitive = (
        _guard(lambda: _count_new_services(session, scan), (0, 0))
        if services
        else (0, 0)
    )
    vuln_counts, kev, new_vulns = (
        _guard(lambda: _count_new_vulnerabilities(session, scan), ({}, 0, 0))
        if vulns
        else ({}, 0, 0)
    )
    return ScanDeltas(
        baseline=hosts or services or vulns,
        new_hosts=_guard(lambda: _count_new_subdomains(session, scan), 0)
        if hosts
        else 0,
        new_services=new_services,
        sensitive_services=sensitive,
        new_vulnerabilities=new_vulns,
        vulnerability_counts=vuln_counts,
        kev=kev,
        dropped_hosts=_guard(lambda: _dropped_hosts(session, scan), 0),
    )


def finalize_scan_run(session: Session, scan: Scan, *, redis_url: str) -> None:
    events = ScanEventPublisher(
        redis_url, scan_id=str(scan.id), project_id=str(scan.project_id)
    )
    notifier = SyncNotificationPublisher(redis_url)
    target_value = (scan.execution_config or {}).get("target_value", "")

    if scan.status in (ScanStatus.COMPLETED.value, ScanStatus.FAILED.value):
        return

    if scan.status == ScanStatus.CANCELLED.value:
        _finalize_user_cancelled(session, scan, events)
        return

    activities = (
        session.execute(select(ScanActivity).where(ScanActivity.scan_id == scan.id))
        .scalars()
        .all()
    )
    status = aggregate_status(activities)
    if status == ScanStatus.RUNNING.value:
        logger.info("finalize deferred: scan %s still has in-flight stages", scan.id)
        return
    truncated = (
        _undispatched(list(activities))
        if status == ScanStatus.COMPLETED.value
        else None
    )
    if truncated:
        status = ScanStatus.FAILED.value
        logger.error("scan %s finalized incomplete: %s", scan.id, truncated)
    counts = derived_counts(session, scan.id)

    # Row-lock + re-check so a concurrent user-cancel (or a duplicate finalize) wins.
    locked = session.get(Scan, scan.id, with_for_update=True)
    if locked is None or locked.status in SCAN_TERMINAL_STATUSES:
        session.commit()
        return

    for column, value in counts.items():
        setattr(locked, column, value)
    locked.status = status
    locked.completed_at = utc_now()
    duration = (
        (locked.completed_at - locked.started_at).total_seconds()
        if locked.started_at
        else None
    )

    if status == ScanStatus.FAILED.value:
        failed = next((a for a in activities if a.error), None)
        locked.error = (
            truncated
            or (
                failed.error if failed and failed.error else "One or more stages failed"
            )
        )[:2000]
    session.add(locked)
    session.commit()
    scan = locked

    if scan.scope == ScanScope.FOCUSED.value:
        try:
            compute_rechecks(session, scan)
        except Exception:
            logger.warning("recheck diff failed for scan %s", scan.id, exc_info=True)

    activity_log = ActivityLogService(session)

    if status == ScanStatus.CANCELLED.value:
        _log_cancelled(activity_log, scan)
        session.commit()
        events.scan_cancelled(status=status)
        return

    if status == ScanStatus.COMPLETED.value:
        activity_log.log(
            event=ActivityEvent.SCAN_COMPLETED,
            title=f"Scan completed · {target_value}",
            description=scan_count_summary(counts),
            level=ActivityLevel.SUCCESS,
            project_id=scan.project_id,
            target_id=scan.target_id,
            scan_id=scan.id,
            target_value=target_value,
        )
        session.commit()
        events.scan_completed(status=status, counts=counts, duration_seconds=duration)
        if scan.scope != ScanScope.FOCUSED.value:
            _dispatch_interest(scan)
            _notify(
                notifier,
                session,
                scan,
                scan_digest(
                    str(scan.id), target_value, counts, _measure(session, scan)
                ),
            )
        return

    activity_log.log(
        event=ActivityEvent.SCAN_FAILED,
        title=f"Scan failed · {target_value}",
        description=scan.error or "One or more stages failed",
        level=ActivityLevel.ERROR,
        project_id=scan.project_id,
        target_id=scan.target_id,
        scan_id=scan.id,
        target_value=target_value,
    )
    session.commit()
    events.scan_failed(status=status, error=scan.error)
    _notify(
        notifier,
        session,
        scan,
        scan_failed(
            str(scan.id), target_value, scan.engine_name, scan.error or "unknown error"
        ),
    )
