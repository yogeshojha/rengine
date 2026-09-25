"""Keep each run's stored first-seen and retired counts current."""

from __future__ import annotations

from uuid import UUID

from celery import shared_task

from app.database import get_sync_session
from shared.logging import get_logger
from shared.models.scan import Scan
from shared.services import locks, scan_deltas

logger = get_logger(__name__)


@shared_task(name="app.tasks.scan_deltas.refresh", max_retries=0)
def refresh(scan_id: str) -> dict:
    with get_sync_session() as session:
        if session.get(Scan, UUID(scan_id)) is None:
            return {"refreshed": False}
        scan_deltas.refresh(session, UUID(scan_id))
    return {"refreshed": True}


@shared_task(name="app.tasks.scan_deltas.backfill", max_retries=0)
def backfill(limit: int = scan_deltas.BACKFILL_SCANS_PER_TICK) -> dict:
    scans = 0
    with (
        get_sync_session() as session,
        locks.sync_lock(session, locks.SCAN_DELTAS_BACKFILL) as held,
    ):
        if not held:
            return {"scans": 0, "more": False, "skipped": "running"}
        pending = scan_deltas.pending_scans(session, limit=limit)
        for scan_id in pending:
            scan = session.get(Scan, scan_id)
            if scan is None:
                continue
            scan_deltas.warm(session, scan)
            scans += 1
    if scans:
        logger.info("scan delta backfill", scans=scans)
    return {"scans": scans, "more": len(pending) >= limit}
