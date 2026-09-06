"""Decide what is worth a look after a scan, and say so once."""

import uuid

from celery import shared_task
from sqlalchemy import select

from app.database import get_sync_session
from shared.config import BaseAppSettings
from shared.definitions.notifications import scan_interesting
from shared.enums.scan import ScanStatus
from shared.logging import get_logger
from shared.models.scan import Scan
from shared.services.ai.config import load_config
from shared.services.interest import (
    ensure_builtin,
    evaluate,
    is_stale,
    new_interesting,
)
from shared.services.notification_sync import SyncNotificationPublisher
from shared.services.orchestrator.events import ScanEventPublisher

logger = get_logger(__name__)

MAX_REFRESH_SCANS = 25


def _publish(scan: Scan, result) -> None:
    try:
        redis_url = BaseAppSettings().redis_url
        events = ScanEventPublisher(
            redis_url, scan_id=str(scan.id), project_id=str(scan.project_id)
        )
        events.interest_ready(
            hosts=result.hosts,
            signals=result.signals,
            bands=result.bands,
            ai_used=result.ai_used,
        )
    except Exception:
        logger.warning("interest event publish failed", exc_info=True)


@shared_task(name="app.tasks.interest.evaluate_scan")
def evaluate_scan(scan_id: str, include_ai: bool = True, notify: bool = True) -> dict:
    with get_sync_session() as session:
        ensure_builtin(session)
        scan = session.get(Scan, uuid.UUID(scan_id))
        if scan is None:
            return {"error": "scan not found"}
        ai = load_config(session)
        result = evaluate(session, scan, ai=ai, include_ai=include_ai)
        logger.info(
            "interest evaluated",
            scan=scan_id,
            hosts=result.hosts,
            signals=result.signals,
            ai=result.ai_used,
            providers=",".join(result.ran),
        )
        if notify:
            _notify(session, scan)
        _publish(scan, result)
        return {
            "hosts": result.hosts,
            "signals": result.signals,
            "ai_used": result.ai_used,
            "providers": result.ran,
        }


def _notify(session, scan: Scan) -> None:
    try:
        leads = new_interesting(session, scan)
        payload = scan_interesting(
            str(scan.id), (scan.execution_config or {}).get("target_value", ""), leads
        )
        if payload is None:
            return
        SyncNotificationPublisher(BaseAppSettings().redis_url).publish(
            session=session,
            type=payload["type"],
            severity=payload["severity"],
            title=payload["title"],
            message=payload["message"],
            metadata=payload.get("metadata"),
            project_id=scan.project_id,
        )
    except Exception:
        logger.warning("interest notification failed", exc_info=True)


@shared_task(name="app.tasks.interest.refresh_project")
def refresh_project(project_id: str) -> dict:
    """A rule change re-labels history; only the rule-driven half is recomputed."""
    refreshed = 0
    with get_sync_session() as session:
        scans = (
            session.execute(
                select(Scan)
                .where(
                    Scan.project_id == uuid.UUID(project_id),
                    Scan.status == ScanStatus.COMPLETED.value,
                )
                .order_by(Scan.created_at.desc())
                .limit(MAX_REFRESH_SCANS)
            )
            .scalars()
            .all()
        )
        ai = load_config(session)
        for scan in scans:
            if not is_stale(session, scan):
                continue
            try:
                evaluate(session, scan, ai=ai, include_ai=False)
                refreshed += 1
            except Exception:
                logger.warning(
                    "interest refresh failed", scan=str(scan.id), exc_info=True
                )
                session.rollback()
    logger.info("interest refreshed", project=project_id, scans=refreshed)
    return {"refreshed": refreshed}
