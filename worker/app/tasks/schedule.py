"""DB-backed scheduler: a 1-minute beat tick fires due scan schedules in the project timezone."""

import uuid

from celery import shared_task
from sqlalchemy import select

from app.database import get_sync_session
from shared.enums.scan_schedule import ScheduleStatus
from shared.logging import get_logger
from shared.models.scan_schedule import ScanSchedule
from shared.services.celery_dispatch import dispatch_scan_run
from shared.services.scan_factory import build_scan_for_target_sync
from shared.services.schedule_timing import advance_schedule
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
        joined[:_MAX_LAST_ERROR].rsplit(";", 1)[0]
        + f" …(+{len(errors)} targets failed)"
    )


def _fire_one(schedule_id: uuid.UUID) -> int:
    """Lock the schedule, advance it, build a PENDING scan per target; dispatch after commit."""
    scan_ids: list[str] = []
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
        errors: list[str] = []
        for tid in uuid_list(sched.target_ids):
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
                )
                scan_ids.append(str(scan.id))
            except Exception as exc:
                errors.append(f"{tid}: {type(exc).__name__}: {exc}")
                logger.warning(
                    "scheduled scan build failed (schedule=%s target=%s): %s",
                    sched.id,
                    tid,
                    exc,
                )
        sched.last_error = _format_errors(errors)
        session.add(sched)
        session.commit()

    dispatched = 0
    for scan_id in scan_ids:
        try:
            dispatch_scan_run(scan_id)
            dispatched += 1
        except Exception:
            logger.warning(
                "scheduled scan dispatch failed (scan=%s)", scan_id, exc_info=True
            )
    if scan_ids and dispatched == 0:
        logger.error(
            "schedule %s built %d scans but dispatched none", schedule_id, len(scan_ids)
        )
    return dispatched


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
