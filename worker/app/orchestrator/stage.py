"""Run one stage with activity tracking."""

import threading
import time
import traceback as tb_mod
import uuid
from collections.abc import Callable

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.database import get_sync_session
from shared.enums.scan import ScanActivityStatus, ScanStatus
from shared.logging import get_logger
from shared.models.scan import Scan
from shared.models.scan_activity import ScanActivity
from shared.services.orchestrator.aggregate import derived_counts
from shared.services.orchestrator.events import ScanEventPublisher
from shared.services.orchestrator.tracking import (
    MAX_STAGE_DELIVERIES,
    ScanActivityService,
    ScanCommandRecorder,
)
from shared.services.scan_resolve import (
    ResolvedScanConfig,
    holding_secrets,
    run_secrets,
    scrub_error,
    unseal_run_config,
)
from shared.utils.datetime import utc_now
from shared.utils.text import sentences
from stages.base import StageAbortedError, StageContext
from stages.registry import StageSpec
from tools.runner.abort import aborting_on

logger = get_logger(__name__)

_ABORT_POLL_SECONDS = 2.0
_HALTED_STATUSES = (ScanStatus.CANCELLED.value, ScanStatus.PAUSED.value)
_UNSETTLED_ACTIVITY_STATUSES = (
    ScanActivityStatus.RUNNING.value,
    ScanActivityStatus.PAUSED.value,
)
_WORKER_LOST = "The worker stopped twice during this stage. Stage not run again."


def _throttled_abort(scan_id: uuid.UUID) -> Callable[[], bool]:
    lock = threading.Lock()
    state = {"at": 0.0, "halted": False}

    def _is_aborted() -> bool:
        with lock:
            if state["halted"]:
                return True
            now = time.monotonic()
            if now - state["at"] < _ABORT_POLL_SECONDS:
                return False
            state["at"] = now
            try:
                state["halted"] = _scan_is_halted(scan_id)
            except Exception:
                logger.warning("abort check failed, keeping last answer", exc_info=True)
            return state["halted"]

    return _is_aborted


def load_resolved(execution_config: dict) -> ResolvedScanConfig:
    raw = execution_config or {}
    clean = unseal_run_config({k: v for k, v in raw.items() if not k.startswith("_")})
    config = ResolvedScanConfig(**clean)
    config._auth_header_names = list(raw.get("_auth_header_names") or [])
    return config


def _scan_is_halted(scan_id: uuid.UUID) -> bool:
    with get_sync_session() as session:
        scan = session.get(Scan, scan_id)
        return scan is None or scan.status in _HALTED_STATUSES


def _halt_status(scan_id: uuid.UUID) -> ScanActivityStatus:
    """PAUSED while the scan is paused, ABORTED otherwise."""
    try:
        with get_sync_session() as session:
            scan = session.get(Scan, scan_id)
            paused = scan is not None and scan.status == ScanStatus.PAUSED.value
    except Exception:
        logger.warning("halt status read failed, recording an abort", exc_info=True)
        return ScanActivityStatus.ABORTED
    return ScanActivityStatus.PAUSED if paused else ScanActivityStatus.ABORTED


def _register_task_id(session: Session, scan: Scan, celery_task_id: str | None) -> None:
    if not celery_task_id:
        return
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
    session.execute(
        update(ScanActivity)
        .where(
            ScanActivity.scan_id == scan.id,
            ScanActivity.name == name,
            ScanActivity.status.in_(_UNSETTLED_ACTIVITY_STATUSES),
        )
        .values(
            status=ScanActivityStatus.SKIPPED.value,
            error="superseded by stage retry",
            completed_at=utc_now(),
        )
    )
    session.commit()


def apply_counts(session: Session, scan: Scan) -> None:
    for column, value in derived_counts(session, scan.id).items():
        setattr(scan, column, value)
    session.add(scan)
    session.commit()


def _open_activity(
    activity_svc: ScanActivityService,
    events: ScanEventPublisher,
    scan: Scan,
    spec: StageSpec,
    celery_task_id: str | None,
) -> ScanActivity | None:
    """The activity row of this run, or None when the stage does not start."""
    _supersede_orphan_activities(activity_svc.session, scan, spec.name)

    done = activity_svc.finished(scan.id, spec.name)
    if done is not None:
        logger.info(
            "stage already finished, not run again",
            scan_id=str(scan.id),
            stage=spec.name,
            status=done.status,
        )
        return None

    redelivered = activity_svc.deliveries(scan.id, spec.name, celery_task_id)
    activity = activity_svc.create(
        scan, name=spec.name, title=spec.title, celery_task_id=celery_task_id
    )

    if redelivered >= MAX_STAGE_DELIVERIES:
        logger.error(
            "stage %s of scan %s lost its worker %s times, not run again",
            spec.name,
            scan.id,
            redelivered,
        )
        _fail_stage(
            activity_svc,
            events,
            spec,
            activity.id,
            ScanActivityStatus.FAILED,
            error=_WORKER_LOST,
        )
        return None

    if scan.status == ScanStatus.CANCELLED.value:
        activity_svc.finish(activity, status=ScanActivityStatus.ABORTED)
        _emit_stage_done(events, spec, activity, ScanActivityStatus.ABORTED.value)
        return None

    return activity


def run_stage(
    session: Session,
    scan: Scan,
    spec: StageSpec,
    *,
    celery_task_id: str | None,
) -> None:
    events = ScanEventPublisher(scan_id=str(scan.id), project_id=str(scan.project_id))
    activity_svc = ScanActivityService(session)
    _register_task_id(session, scan, celery_task_id)

    activity = _open_activity(activity_svc, events, scan, spec, celery_task_id)
    if activity is None:
        return

    events.stage_started(activity_id=activity.id, stage=spec.name, title=spec.title)

    secrets: list[str] = []
    try:
        resolved = load_resolved(scan.execution_config)
        secrets = run_secrets(resolved)
        recorder = ScanCommandRecorder(
            session_factory=get_sync_session,
            scan_id=scan.id,
            project_id=scan.project_id,
            activity_id=activity.id,
            events=events,
            secrets=secrets,
        )

        if resolved.target_type not in spec.applies_to:
            activity_svc.finish(
                activity,
                status=ScanActivityStatus.SKIPPED,
                result={"reason": "not applicable to this target type"},
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
            is_aborted=_throttled_abort(scan.id),
        )
        stage = spec.stage_cls(session, ctx)

        if not stage.should_run():
            activity_svc.finish(
                activity,
                status=ScanActivityStatus.SKIPPED,
                result={"reason": "not applicable to this target or configuration"},
            )
            _emit_stage_done(events, spec, activity, ScanActivityStatus.SKIPPED.value)
            return

        with aborting_on(ctx.is_aborted), holding_secrets(resolved):
            result = stage.run()
        # a killed tool returns normally
        if _scan_is_halted(scan.id):
            raise StageAbortedError
    except StageAbortedError:
        _fail_stage(
            activity_svc,
            events,
            spec,
            activity.id,
            _halt_status(scan.id),
        )
        return
    except Exception as exc:
        reason = scrub_error(str(exc), secrets)
        logger.error("stage %s failed for scan %s: %s", spec.name, scan.id, reason)
        _fail_stage(
            activity_svc,
            events,
            spec,
            activity.id,
            ScanActivityStatus.FAILED,
            error=reason,
            traceback=scrub_error(tb_mod.format_exc(), secrets),
        )
        return

    status = (
        ScanActivityStatus.PARTIAL if result.partial else ScanActivityStatus.SUCCESS
    )
    notes = scrub_error(sentences(result.warnings), secrets) or None
    activity_svc.finish(activity, status=status, result=result.counts, error=notes)
    try:
        scan = session.get(Scan, scan.id)
        if scan is not None:
            apply_counts(session, scan)
    except Exception:
        logger.warning(
            "stage bookkeeping failed after a terminal activity", exc_info=True
        )
        session.rollback()
    _emit_stage_done(events, spec, activity, status.value, counts=result.counts)


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
    if activity is None:
        logger.warning(
            "stage activity %s vanished before its failure was recorded", activity_id
        )
        return
    try:
        activity_svc.finish(activity, status=status, error=error, traceback=traceback)
    except Exception:
        logger.warning("stage failure could not be recorded in full", exc_info=True)
        activity_svc.session.rollback()
        try:
            activity_svc.finish(activity, status=status, error="stage failed")
        except Exception:
            logger.error(
                "stage activity %s could not be finished", activity_id, exc_info=True
            )
            activity_svc.session.rollback()
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
