"""Run one engine stage, fully tracked (activity timeline, command registration, events, abort)."""

import traceback as tb_mod
import uuid
from collections.abc import Callable

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.database import get_sync_session
from engines.base import EngineAbortedError, EngineContext
from engines.registry import StageSpec
from shared.enums.scan import ScanActivityStatus, ScanStatus
from shared.logging import get_logger
from shared.models.scan import Scan
from shared.models.scan_activity import ScanActivity
from shared.services.orchestrator.aggregate import COUNT_TO_COLUMN
from shared.services.orchestrator.events import ScanEventPublisher
from shared.services.orchestrator.tracking import (
    ScanActivityService,
    ScanCommandRecorder,
)
from shared.services.scan_resolve import ResolvedScanConfig
from shared.utils.datetime import utc_now

logger = get_logger(__name__)


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
            status=ScanActivityStatus.FAILED.value,
            error="superseded by stage retry",
            completed_at=utc_now(),
        )
    )
    session.commit()


def _apply_counts(session: Session, scan: Scan, counts: dict) -> None:
    for key, column in COUNT_TO_COLUMN.items():
        value = counts.get(key)
        if isinstance(value, int):
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

    ctx = EngineContext(
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
        is_aborted=lambda: _scan_is_cancelled(session_factory, scan.id),
    )
    engine = spec.engine_cls(session, ctx)

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
    except EngineAbortedError:
        _fail_stage(activity_svc, events, spec, activity.id, ScanActivityStatus.ABORTED)
        return
    except Exception as exc:
        logger.error("stage %s failed for scan %s: %s", spec.name, scan.id, exc)
        _fail_stage(
            activity_svc,
            events,
            spec,
            activity.id,
            ScanActivityStatus.FAILED,
            error=str(exc),
            traceback=tb_mod.format_exc(),
        )
        return

    activity_svc.finish(
        activity, status=ScanActivityStatus.SUCCESS, result=result.counts
    )
    scan = session.get(Scan, scan.id)
    if scan is not None:
        _apply_counts(session, scan, result.counts)
    _emit_stage_done(
        events,
        spec,
        activity,
        ScanActivityStatus.SUCCESS.value,
        counts=result.counts,
    )


def _fail_stage(
    activity_svc: ScanActivityService,
    events: ScanEventPublisher,
    spec: StageSpec,
    activity_id: uuid.UUID,
    status: ScanActivityStatus,
    *,
    error: str | None = None,
    traceback: str | None = None,
) -> None:
    activity_svc.session.rollback()
    activity = activity_svc.session.get(ScanActivity, activity_id)
    activity_svc.finish(activity, status=status, error=error, traceback=traceback)
    _emit_stage_done(events, spec, activity, status.value)


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
