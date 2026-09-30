"""Decide which assets are exposures after a scan."""

import contextlib
import uuid
from contextlib import contextmanager

from celery import shared_task
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError

from app.database import get_sync_session
from app.orchestrator.finalize import notify_digest
from shared.config import BaseAppSettings
from shared.enums.scan import SCAN_TERMINAL_STATUSES, ScanStatus
from shared.logging import get_logger
from shared.models.scan import Scan
from shared.services.ai.config import load_config
from shared.services.asset_query.lead_cache import bump_sync
from shared.services.interest import (
    LIVE_SOURCES,
    count_new_interesting,
    ensure_builtin,
    evaluate,
    is_stale,
)
from shared.services.orchestrator.events import ScanEventPublisher

logger = get_logger(__name__)

MAX_REFRESH_SCANS = 25
LIVE_LOCK_TIMEOUT_S = 5


@contextmanager
def _yield_to_scans(session):
    """Bound how long a judgement may hold host-row locks, then put the connection back as found."""
    session.execute(text(f"SET SESSION lock_timeout = '{LIVE_LOCK_TIMEOUT_S}s'"))
    try:
        yield
    finally:
        with contextlib.suppress(Exception):
            session.execute(text("RESET lock_timeout"))


def _publish(scan: Scan, result) -> None:
    try:
        redis_url = BaseAppSettings().redis_url
        bump_sync((scan.target_id,), redis_url)
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
def evaluate_scan(scan_id: str, include_ai: bool = True, digest: bool = False) -> dict:
    with get_sync_session() as session:
        ensure_builtin(session)
        scan = session.get(Scan, uuid.UUID(scan_id))
        if scan is None:
            return {"error": "scan not found"}
        scored = False
        try:
            ai = load_config(session)
            with _yield_to_scans(session):
                result = evaluate(session, scan, ai=ai, include_ai=include_ai)
            scored = True
        except OperationalError:
            session.rollback()
            logger.info("interest evaluation yielded to a running scan", scan=scan_id)
            return {"skipped": "busy"}
        finally:
            if digest:
                _digest(session, scan, scored=scored)
        logger.info(
            "interest evaluated",
            scan=scan_id,
            hosts=result.hosts,
            signals=result.signals,
            ai=result.ai_used,
            providers=",".join(result.ran),
        )
        _publish(scan, result)
        return {
            "hosts": result.hosts,
            "signals": result.signals,
            "ai_used": result.ai_used,
            "providers": result.ran,
        }


@shared_task(name="app.tasks.interest.evaluate_live")
def evaluate_live(scan_id: str) -> dict:
    """Judge a running scan from its rules alone."""
    with get_sync_session() as session:
        scan = session.get(Scan, uuid.UUID(scan_id))
        if scan is None or scan.status in SCAN_TERMINAL_STATUSES:
            return {"skipped": "run is over"}
        try:
            with _yield_to_scans(session):
                ensure_builtin(session)
                result = evaluate(session, scan, include_ai=False, only=LIVE_SOURCES)
        except OperationalError:
            session.rollback()
            logger.info("live interest pass yielded to the scan", scan=scan_id)
            return {"skipped": "busy"}
        _publish(scan, result)
        return {"hosts": result.hosts, "signals": result.signals, "live": True}


def _digest(session, scan: Scan, *, scored: bool) -> None:
    try:
        exposures = count_new_interesting(session, scan) if scored else 0
    except Exception:
        session.rollback()
        logger.warning("exposure count failed", exc_info=True)
        exposures = 0
    notify_digest(session, scan, exposures)


@shared_task(name="app.tasks.interest.refresh_project")
def refresh_project(project_id: str) -> dict:
    """A rule change re-labels history."""
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
