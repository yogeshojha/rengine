"""Hash stored screenshots and hold them as WebP."""

from __future__ import annotations

from celery import shared_task
from sqlalchemy import select

from app.database import get_sync_session
from shared.logging import get_logger
from shared.models.scan import Scan
from shared.services import screenshot_store
from shared.services.asset_query.lead_cache import bump_sync

logger = get_logger(__name__)


@shared_task(name="app.tasks.screenshots.backfill", max_retries=0)
def backfill(limit: int = screenshot_store.SCANS_PER_TICK) -> dict:
    scans = 0
    rows = 0
    reclaimed = 0
    with get_sync_session() as session:
        pending = screenshot_store.pending_scans(session, limit=limit)
        for scan_id in pending:
            touched, bytes_freed = screenshot_store.process_scan(session, scan_id)
            rows += touched
            reclaimed += bytes_freed
            scans += 1
            target = session.execute(
                select(Scan.target_id).where(Scan.id == scan_id)
            ).scalar_one_or_none()
            if target is not None:
                bump_sync([target])
    if scans:
        logger.info("screenshot backfill", scans=scans, rows=rows, reclaimed=reclaimed)
    return {
        "scans": scans,
        "rows": rows,
        "reclaimed": reclaimed,
        "more": len(pending) >= limit,
    }
