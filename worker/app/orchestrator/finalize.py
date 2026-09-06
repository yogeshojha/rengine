"""Aggregate stage outcomes into the final scan status + terminal notification/event."""

from sqlalchemy import Integer, String, bindparam, func, select, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Session

from shared.definitions.notifications import (
    scan_cancelled,
    scan_completed,
    scan_count_summary,
    scan_failed,
    scan_new_services,
    scan_new_subdomains,
    scan_new_vulnerabilities,
    scan_vulnerability_coverage,
)
from shared.definitions.ports import SENSITIVE_PORTS
from shared.definitions.vulnerabilities import SUPPRESSED_STATES, CoverageStatus
from shared.enums.activity import ActivityEvent, ActivityLevel
from shared.enums.scan import SCAN_TERMINAL_STATUSES, ScanScope, ScanStatus
from shared.logging import get_logger
from shared.models.scan import Scan
from shared.models.scan_activity import ScanActivity
from shared.models.subdomain import Subdomain
from shared.models.vulnerability import VulnerabilityCoverage
from shared.services.activity_log import ActivityLogService
from shared.services.notification_sync import SyncNotificationPublisher
from shared.services.orchestrator import (
    aggregate_counts,
    aggregate_status,
    derived_counts,
)
from shared.services.orchestrator.events import ScanEventPublisher
from shared.services.recheck import compute_rechecks
from shared.utils.datetime import utc_now

logger = get_logger(__name__)


def _notify(
    notifier: SyncNotificationPublisher, session: Session, payload: dict
) -> None:
    try:
        notifier.publish(
            session=session,
            type=payload["type"],
            severity=payload["severity"],
            title=payload["title"],
            message=payload["message"],
            metadata=payload.get("metadata"),
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


def _count_new_subdomains(session: Session, scan: Scan) -> int:
    """Subdomain names this scan was the first to discover for its target."""
    rn = (
        func.row_number()
        .over(
            partition_by=[Subdomain.target_id, Subdomain.name],
            order_by=[Subdomain.discovered_at.asc(), Subdomain.scan_id.asc()],
        )
        .label("rn")
    )
    firsts = (
        select(Subdomain.scan_id.label("scan_id"), rn)
        .where(Subdomain.target_id == scan.target_id)
        .subquery()
    )
    return (
        session.execute(
            select(func.count()).where(firsts.c.rn == 1, firsts.c.scan_id == scan.id)
        ).scalar_one()
        or 0
    )


_NEW_SERVICES_SQL = """
SELECT count(*) AS total,
       count(*) FILTER (WHERE p.number = ANY(:sensitive_ports)) AS sensitive
FROM ports p
WHERE p.scan_id = :sid
  AND EXISTS (
      SELECT 1 FROM ports b
      WHERE b.target_id = p.target_id AND b.scan_id <> :sid
        AND b.discovered_at < p.discovered_at
  )
  AND NOT EXISTS (
      SELECT 1 FROM ports e
      WHERE e.target_id = p.target_id AND e.ip = p.ip AND e.number = p.number
        AND e.scan_id <> :sid AND e.discovered_at < p.discovered_at
  )
"""


def _count_new_services(session: Session, scan: Scan) -> tuple[int, int]:
    """Ports this scan is the first to see for its target, and how many are sensitive."""
    row = session.execute(
        text(_NEW_SERVICES_SQL).bindparams(
            bindparam("sid", scan.id),
            bindparam("sensitive_ports", SENSITIVE_PORTS, type_=ARRAY(Integer)),
        )
    ).one()
    return int(row.total or 0), int(row.sensitive or 0)


# findings this scan is the first to report for its target, by severity
_NEW_VULNS_SQL = """
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
  AND EXISTS (
      SELECT 1 FROM vulnerabilities b
      WHERE b.target_id = v.target_id AND b.scan_id <> :sid
        AND b.discovered_at < v.discovered_at
  )
  AND NOT EXISTS (
      SELECT 1 FROM vulnerabilities e
      WHERE e.target_id = v.target_id AND e.fingerprint = v.fingerprint
        AND e.scan_id <> :sid AND e.discovered_at < v.discovered_at
  )
GROUP BY v.severity
"""


def _count_new_vulnerabilities(session: Session, scan: Scan) -> tuple[dict, int, int]:
    """New findings for this target, by severity, excluding anything a reviewer set aside."""
    rows = session.execute(
        text(_NEW_VULNS_SQL).bindparams(
            bindparam("sid", scan.id),
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


def _notify_deltas(
    notifier: SyncNotificationPublisher, session: Session, scan: Scan, target: str
) -> None:
    """Announce what this scan found that the previous one did not."""
    try:
        new_subs = _count_new_subdomains(session, scan)
        if new_subs > 0:
            _notify(
                notifier, session, scan_new_subdomains(str(scan.id), target, new_subs)
            )
    except Exception:
        logger.warning("new-subdomain notification failed", exc_info=True)
    try:
        new_services, sensitive = _count_new_services(session, scan)
        if new_services > 0:
            _notify(
                notifier,
                session,
                scan_new_services(str(scan.id), target, new_services, sensitive),
            )
    except Exception:
        logger.warning("new-service notification failed", exc_info=True)
    try:
        counts, kev, total = _count_new_vulnerabilities(session, scan)
        if total > 0:
            _notify(
                notifier,
                session,
                scan_new_vulnerabilities(str(scan.id), target, counts, kev, total),
            )
        dropped = _dropped_hosts(session, scan)
        if dropped > 0:
            _notify(
                notifier,
                session,
                scan_vulnerability_coverage(str(scan.id), target, dropped),
            )
    except Exception:
        logger.warning("vulnerability notification failed", exc_info=True)


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
    counts = {**aggregate_counts(activities), **derived_counts(session, scan.id)}

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
            failed.error if failed and failed.error else "One or more stages failed"
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
        _notify(
            notifier,
            session,
            scan_cancelled(str(scan.id), target_value, scan.engine_name),
        )
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
            _notify(
                notifier,
                session,
                scan_completed(
                    str(scan.id), target_value, scan.engine_name, counts, duration
                ),
            )
        _notify_deltas(notifier, session, scan, target_value)
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
        scan_failed(
            str(scan.id), target_value, scan.engine_name, scan.error or "unknown error"
        ),
    )
