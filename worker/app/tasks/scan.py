"""Scan orchestrator celery tasks: run_scan (dispatch canvas), run_scan_stage, finalize_scan."""

import uuid

from celery import shared_task

from app.config import settings
from app.database import get_sync_session
from app.orchestrator import build_canvas, finalize_scan_run, run_stage
from shared.definitions.notifications import scan_started
from shared.enums.activity import ActivityEvent, ActivityLevel
from shared.enums.scan import SCAN_TERMINAL_STATUSES, ScanStatus
from shared.logging import get_logger
from shared.models.scan import Scan
from shared.services.activity_log import ActivityLogService
from shared.services.notification_sync import SyncNotificationPublisher
from shared.services.orchestrator.events import ScanEventPublisher
from shared.utils.datetime import utc_now
from stages.registry import get_stage

logger = get_logger(__name__)

# run_scan id + canvas root id — a RUNNING scan with fewer was claimed but not dispatched.
_DISPATCHED_TASK_IDS = 2


def _send_notif(redis_url: str, session, payload: dict) -> None:
    try:
        SyncNotificationPublisher(redis_url).publish(
            session=session,
            type=payload["type"],
            severity=payload["severity"],
            title=payload["title"],
            message=payload["message"],
            metadata=payload.get("metadata"),
        )
    except Exception:
        logger.warning("scan notification dispatch failed", exc_info=True)


@shared_task(bind=True, name="app.tasks.scan.run_scan", max_retries=0)
def run_scan(self, scan_id: str) -> dict:
    """Orchestrator entrypoint: claim RUNNING, dispatch the stage canvas, then notify."""
    redis_url = settings.celery_broker_url
    with get_sync_session() as session:
        scan = session.get(Scan, uuid.UUID(scan_id))
        if scan is None:
            logger.warning("scan %s not found", scan_id)
            return {"error": "scan not found"}
        if scan.status in SCAN_TERMINAL_STATUSES:
            logger.info("scan %s already %s, skipping", scan_id, scan.status)
            return {"skipped": scan.status}
        if (
            scan.status == ScanStatus.RUNNING.value
            and len(scan.celery_task_ids or []) >= _DISPATCHED_TASK_IDS
        ):
            logger.info("scan %s canvas already dispatched, skipping", scan_id)
            return {"skipped": "already dispatched"}

        was_pending = scan.status == ScanStatus.PENDING.value
        if was_pending:
            scan.status = ScanStatus.RUNNING.value
            scan.started_at = utc_now()
            scan.error = None
        scan.celery_task_ids = [self.request.id]
        session.commit()

        workflow = build_canvas(scan_id)
        result = workflow.apply_async()
        scan.celery_task_ids = [self.request.id, result.id]
        session.commit()
        logger.info("scan %s canvas dispatched (root=%s)", scan_id, result.id)

        if was_pending:
            events = ScanEventPublisher(
                redis_url, scan_id=scan_id, project_id=str(scan.project_id)
            )
            target_value = (scan.execution_config or {}).get("target_value", "")
            ActivityLogService(session).log(
                event=ActivityEvent.SCAN_STARTED,
                title=f"Scan started · {target_value}",
                description=scan.engine_name,
                level=ActivityLevel.INFO,
                project_id=scan.project_id,
                target_id=scan.target_id,
                scan_id=scan.id,
                target_value=target_value,
            )
            session.commit()
            events.scan_started(status=scan.status, engine=scan.engine_name)
            _send_notif(
                redis_url,
                session,
                scan_started(scan_id, target_value, scan.engine_name),
            )
        return {"dispatched": True, "task_id": result.id}


@shared_task(bind=True, name="app.tasks.scan.run_scan_stage", max_retries=0)
def run_scan_stage(self, scan_id: str, stage_name: str) -> dict:
    """Run one engine stage with activity tracking + command registration."""
    spec = get_stage(stage_name)
    if spec is None:
        logger.warning("unknown scan stage %s", stage_name)
        return {"error": "unknown stage", "stage": stage_name}

    with get_sync_session() as session:
        scan = session.get(Scan, uuid.UUID(scan_id))
        if scan is None:
            return {"error": "scan not found"}
        run_stage(
            session,
            scan,
            spec,
            celery_task_id=self.request.id,
            redis_url=settings.celery_broker_url,
        )
    return {"stage": stage_name}


@shared_task(bind=True, name="app.tasks.scan.finalize_scan", max_retries=0)
def finalize_scan(self, scan_id: str) -> dict:  # noqa: ARG001
    """Aggregate stage outcomes into the final scan status + terminal notif."""
    with get_sync_session() as session:
        scan = session.get(Scan, uuid.UUID(scan_id))
        if scan is None:
            return {"error": "scan not found"}
        finalize_scan_run(session, scan, redis_url=settings.celery_broker_url)
    return {"finalized": True, "scan_id": scan_id}
