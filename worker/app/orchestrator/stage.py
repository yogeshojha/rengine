"""Run one engine stage, fully tracked (activity timeline, command registration, events, abort)."""

import threading
import time
import traceback as tb_mod
import uuid
from collections.abc import Callable
from typing import NamedTuple

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.database import get_sync_session
from shared.definitions.notifications import stage_count_summary
from shared.enums.activity import ActivityEvent, ActivityLevel
from shared.enums.scan import ScanActivityStatus, ScanStatus
from shared.logging import get_logger
from shared.models.scan import Scan
from shared.models.scan_activity import ScanActivity
from shared.services.activity_log import ActivityLogService
from shared.services.orchestrator.aggregate import aggregate_counts, derived_counts
from shared.services.orchestrator.events import ScanEventPublisher
from shared.services.orchestrator.tracking import (
    ScanActivityService,
    ScanCommandRecorder,
)
from shared.services.scan_resolve import ResolvedScanConfig
from shared.utils.datetime import utc_now
from stages.base import StageAbortedError, StageContext
from stages.registry import StageSpec

logger = get_logger(__name__)

# stages call _check_abort() in tight loops (once per resolved name, per finding, per
# root), so the cancel flag is polled at most this often instead of once per call
_ABORT_POLL_SECONDS = 2.0


def _throttled_abort(
    session_factory: Callable[[], Session], scan_id: uuid.UUID
) -> Callable[[], bool]:
    lock = threading.Lock()
    state = {"at": 0.0, "cancelled": False}

    def _is_aborted() -> bool:
        with lock:
            if state["cancelled"]:
                return True
            now = time.monotonic()
            if now - state["at"] < _ABORT_POLL_SECONDS:
                return False
            state["at"] = now
            state["cancelled"] = _scan_is_cancelled(session_factory, scan_id)
            return state["cancelled"]

    return _is_aborted


def load_resolved(execution_config: dict) -> ResolvedScanConfig:
    clean = {k: v for k, v in (execution_config or {}).items() if not k.startswith("_")}
    return ResolvedScanConfig(**clean)


def _scan_is_cancelled(
    session_factory: Callable[[], Session], scan_id: uuid.UUID
) -> bool:
    with session_factory() as session:
        scan = session.get(Scan, scan_id)
        return scan is not None and scan.status == ScanStatus.CANCELLED.value


def _register_task_id(session: Session, scan: Scan, celery_task_id: str | None) -> None:
    if not celery_task_id:
        return
    # Row-lock the append so concurrent parallel stages don't drop ids (abort handle).
    locked = session.get(Scan, scan.id, with_for_update=True)
    if locked is None:
        session.commit()
        return
    ids = list(locked.celery_task_ids or [])
    if celery_task_id not in ids:
        ids.append(celery_task_id)
        locked.celery_task_ids = ids
        session.add(locked)
    session.commit()


def _supersede_orphan_activities(session: Session, scan: Scan, name: str) -> None:
    # redelivery re-runs this stage — fail the orphan RUNNING row so finalize isn't blocked
    session.execute(
        update(ScanActivity)
        .where(
            ScanActivity.scan_id == scan.id,
            ScanActivity.name == name,
            ScanActivity.status == ScanActivityStatus.RUNNING.value,
        )
        .values(
            status=ScanActivityStatus.SKIPPED.value,
            error="superseded by stage retry",
            completed_at=utc_now(),
        )
    )
    session.commit()


def _apply_counts(session: Session, scan: Scan) -> None:
    # roll up across every finished stage so a later stage's 0 never clobbers an earlier total
    activities = (
        session.execute(select(ScanActivity).where(ScanActivity.scan_id == scan.id))
        .scalars()
        .all()
    )
    totals = {**aggregate_counts(activities), **derived_counts(session, scan.id)}
    for column, value in totals.items():
        setattr(scan, column, value)
    session.add(scan)
    session.commit()


def run_stage(
    session: Session,
    scan: Scan,
    spec: StageSpec,
    *,
    celery_task_id: str | None,
    redis_url: str,
    session_factory: Callable[[], Session] = get_sync_session,
) -> None:
    events = ScanEventPublisher(
        redis_url, scan_id=str(scan.id), project_id=str(scan.project_id)
    )
    activity_svc = ScanActivityService(session)
    ids = _ScanIds(
        scan.id,
        scan.project_id,
        scan.target_id,
        (scan.execution_config or {}).get("target_value", ""),
    )
    _register_task_id(session, scan, celery_task_id)
    _supersede_orphan_activities(session, scan, spec.name)

    activity = activity_svc.create(
        scan, name=spec.name, title=spec.title, celery_task_id=celery_task_id
    )

    if scan.status == ScanStatus.CANCELLED.value:
        activity_svc.finish(activity, status=ScanActivityStatus.ABORTED)
        _emit_stage_done(events, spec, activity, ScanActivityStatus.ABORTED.value)
        return

    events.stage_started(activity_id=activity.id, stage=spec.name, title=spec.title)

    recorder = ScanCommandRecorder(
        session_factory=session_factory,
        scan_id=scan.id,
        project_id=scan.project_id,
        activity_id=activity.id,
        events=events,
    )
    resolved = load_resolved(scan.execution_config)

    if resolved.target_type not in spec.applies_to:
        activity_svc.finish(
            activity,
            status=ScanActivityStatus.SKIPPED,
            result={"reason": "not applicable for target type"},
        )
        _emit_stage_done(events, spec, activity, ScanActivityStatus.SKIPPED.value)
        return

    ctx = StageContext(
        scan_id=scan.id,
        target_id=scan.target_id,
        project_id=scan.project_id,
        target_value=resolved.target_value,
        target_type=resolved.target_type,
        resolved=resolved,
        activity_id=activity.id,
        stage_name=spec.name,
        recorder=recorder,
        events=events,
        is_aborted=_throttled_abort(session_factory, scan.id),
    )
    engine = spec.stage_cls(session, ctx)

    if not engine.should_run():
        activity_svc.finish(
            activity,
            status=ScanActivityStatus.SKIPPED,
            result={"reason": "not applicable for this target/config"},
        )
        _emit_stage_done(events, spec, activity, ScanActivityStatus.SKIPPED.value)
        return

    try:
        result = engine.run()
    except StageAbortedError:
        _fail_stage(
            activity_svc, events, spec, activity.id, ScanActivityStatus.ABORTED, ids
        )
        return
    except Exception as exc:
        logger.error("stage %s failed for scan %s: %s", spec.name, scan.id, exc)
        _fail_stage(
            activity_svc,
            events,
            spec,
            activity.id,
            ScanActivityStatus.FAILED,
            ids,
            error=str(exc),
            traceback=tb_mod.format_exc(),
        )
        return

    # a stage that ran but came up short reports PARTIAL — never a silent success
    status = (
        ScanActivityStatus.PARTIAL if result.partial else ScanActivityStatus.SUCCESS
    )
    notes = "; ".join(result.warnings) or None
    activity_svc.finish(activity, status=status, result=result.counts, error=notes)
    _log_stage(
        session,
        spec,
        ids,
        ActivityEvent.SCAN_STAGE_COMPLETED,
        summary=stage_count_summary(result.counts),
        warning=notes if result.partial else None,
    )
    scan = session.get(Scan, scan.id)
    if scan is not None:
        _apply_counts(session, scan)
    _emit_stage_done(events, spec, activity, status.value, counts=result.counts)


def _fail_stage(
    activity_svc: ScanActivityService,
    events: ScanEventPublisher,
    spec: StageSpec,
    activity_id: uuid.UUID,
    status: ScanActivityStatus,
    ids: "_ScanIds",
    *,
    error: str | None = None,
    traceback: str | None = None,
) -> None:
    activity_svc.session.rollback()
    activity = activity_svc.session.get(ScanActivity, activity_id)
    activity_svc.finish(activity, status=status, error=error, traceback=traceback)
    if status == ScanActivityStatus.FAILED:
        _log_stage(
            activity_svc.session,
            spec,
            ids,
            ActivityEvent.SCAN_STAGE_FAILED,
            error=error,
        )
    _emit_stage_done(events, spec, activity, status.value)


class _ScanIds(NamedTuple):
    scan_id: uuid.UUID
    project_id: uuid.UUID
    target_id: uuid.UUID
    target_value: str


def _log_stage(
    session: Session,
    spec: StageSpec,
    ids: _ScanIds,
    event: ActivityEvent,
    *,
    summary: str | None = None,
    error: str | None = None,
    warning: str | None = None,
) -> None:
    failed = event == ActivityEvent.SCAN_STAGE_FAILED
    if failed:
        description, level = error or "stage failed", ActivityLevel.ERROR
    elif warning:
        description, level = warning, ActivityLevel.WARNING
    else:
        description, level = summary, ActivityLevel.INFO
    ActivityLogService(session).log(
        event=event,
        title=spec.title,
        description=description,
        level=level,
        project_id=ids.project_id,
        target_id=ids.target_id,
        scan_id=ids.scan_id,
        target_value=ids.target_value or None,
    )
    session.commit()


def _emit_stage_done(
    events: ScanEventPublisher,
    spec: StageSpec,
    activity: ScanActivity,
    status: str,
    counts: dict | None = None,
) -> None:
    events.stage_completed(
        activity_id=activity.id, stage=spec.name, status=status, counts=counts
    )
