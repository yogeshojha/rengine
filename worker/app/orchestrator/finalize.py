"""Aggregate stage outcomes into the final scan status + terminal notification/event."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from shared.definitions.notifications import (
    scan_cancelled,
    scan_completed,
    scan_count_summary,
    scan_failed,
    scan_new_subdomains,
)
from shared.enums.activity import ActivityEvent, ActivityLevel
from shared.enums.scan import SCAN_TERMINAL_STATUSES, ScanStatus
from shared.logging import get_logger
from shared.models.scan import Scan
from shared.models.scan_activity import ScanActivity
from shared.models.subdomain import Subdomain
from shared.services.activity_log import ActivityLogService
from shared.services.notification_sync import SyncNotificationPublisher
from shared.services.orchestrator import aggregate_counts, aggregate_status
from shared.services.orchestrator.events import ScanEventPublisher
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
    counts = aggregate_counts(activities)

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
        _notify(
            notifier,
            session,
            scan_completed(
                str(scan.id), target_value, scan.engine_name, counts, duration
            ),
        )
        try:
            new_subs = _count_new_subdomains(session, scan)
            if new_subs > 0:
                _notify(
                    notifier,
                    session,
                    scan_new_subdomains(str(scan.id), target_value, new_subs),
                )
        except Exception:
            logger.warning("new-subdomain notification failed", exc_info=True)
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
