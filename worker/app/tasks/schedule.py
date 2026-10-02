"""DB-backed scheduler: a 1-minute beat tick fires due scan schedules in the project timezone."""

import uuid

from celery import shared_task
from sqlalchemy import select

from app.database import get_sync_session
from shared.definitions.notifications import schedule_not_started
from shared.enums.scan_schedule import ScheduleStatus
from shared.logging import get_logger
from shared.models.scan_schedule import ScanSchedule
from shared.models.target import Target
from shared.services.celery_dispatch import dispatch_scan_run
from shared.services.notification_sync import SyncNotificationPublisher
from shared.services.scan_factory import ScanFactoryError, build_scan_for_target_sync
from shared.services.schedule_timing import advance_schedule
from shared.utils.crypto import SecretDecryptionError
from shared.utils.datetime import utc_now
from shared.utils.uuid import uuid_list

logger = get_logger(__name__)

_MAX_LAST_ERROR = 2000


def _format_errors(errors: list[str]) -> str | None:
    if not errors:
        return None
    joined = "; ".join(errors)
    if len(joined) <= _MAX_LAST_ERROR:
        return joined
    return (
        joined[:_MAX_LAST_ERROR].rsplit(";", 1)[0] + f". {len(errors)} targets failed."
    )


def _fire_one(schedule_id: uuid.UUID) -> int:
    """Lock the schedule, advance it, build a PENDING scan per target."""
    queued: list[tuple[str, int]] = []
    errors: list[str] = []
    with get_sync_session() as session:
        sched = session.execute(
            select(ScanSchedule)
            .where(ScanSchedule.id == schedule_id)
            .with_for_update(skip_locked=True)
        ).scalar_one_or_none()
        if sched is None:
            return 0
        if (
            sched.status != ScheduleStatus.ACTIVE.value
            or sched.next_run_at is None
            or sched.next_run_at > utc_now()
        ):
            return 0

        advance_schedule(sched, fired_at=utc_now())
        name, project_id, total = (
            sched.name,
            sched.project_id,
            len(sched.target_ids or []),
        )
        target_ids = uuid_list(sched.target_ids)
        labels = dict(
            session.execute(
                select(Target.id, Target.target_value).where(Target.id.in_(target_ids))
            ).all()
        )
        for tid in target_ids:
            label = labels.get(tid, tid)
            try:
                scan = build_scan_for_target_sync(
                    session,
                    project_id=sched.project_id,
                    target_id=tid,
                    engine_id=sched.engine_id,
                    context_id=sched.context_id,
                    created_by=sched.created_by,
                    schedule_id=sched.id,
                    schedule_type=sched.schedule_type,
                    intensity=sched.intensity,
                )
                queued.append((str(scan.id), scan.run_epoch))
            except Exception as exc:
                reason = (
                    exc
                    if isinstance(exc, ScanFactoryError | SecretDecryptionError)
                    else "Scan not created."
                )
                errors.append(f"{label}: {reason}")
                logger.warning(
                    "scheduled scan build failed (schedule=%s target=%s): %s: %s",
                    sched.id,
                    tid,
                    type(exc).__name__,
                    exc,
                )
        sched.last_error = _format_errors(errors)
        session.add(sched)
        session.commit()

    dispatched = 0
    for scan_id, epoch in queued:
        try:
            dispatch_scan_run(scan_id, epoch)
            dispatched += 1
        except Exception:
            logger.warning(
                "scheduled scan dispatch failed (scan=%s)", scan_id, exc_info=True
            )
    if queued and dispatched == 0:
        logger.error(
            "schedule %s built %d scans but dispatched none", schedule_id, len(queued)
        )
    failed = len(errors) + len(queued) - dispatched
    if failed:
        _notify_not_started(name, project_id, failed, total)
    return dispatched


def _notify_not_started(name: str, project_id, failed: int, total: int) -> None:
    payload = schedule_not_started(name, failed, total)
    try:
        with get_sync_session() as session:
            SyncNotificationPublisher().publish(
                session=session,
                type=payload["type"],
                severity=payload["severity"],
                title=payload["title"],
                message=payload["message"],
                metadata=payload["metadata"],
                project_id=project_id,
            )
    except Exception:
        logger.warning("schedule notification failed", exc_info=True)


@shared_task(name="app.tasks.schedule.tick")
def tick() -> dict:
    """Fire every scan schedule whose next_run_at has elapsed."""
    with get_sync_session() as session:
        now = utc_now()
        due_ids = (
            session.execute(
                select(ScanSchedule.id).where(
                    ScanSchedule.status == ScheduleStatus.ACTIVE.value,
                    ScanSchedule.next_run_at.is_not(None),
                    ScanSchedule.next_run_at <= now,
                )
            )
            .scalars()
            .all()
        )
    spawned = sum(_fire_one(sid) for sid in due_ids)
    if due_ids:
        logger.info("schedule tick: %d due, %d scans dispatched", len(due_ids), spawned)
    return {"due": len(due_ids), "scans": spawned}
