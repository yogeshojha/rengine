"""Backfill hygiene checks over stored responses."""

from __future__ import annotations

from celery import shared_task
from sqlalchemy import select

from app.database import get_sync_session
from shared.definitions.hygiene import BACKFILL_SCANS_PER_TICK
from shared.logging import get_logger
from shared.models.scan import Scan
from shared.services import web_hygiene
from shared.services.asset_query.lead_cache import bump_sync

logger = get_logger(__name__)


@shared_task(name="app.tasks.hygiene.backfill", max_retries=0)
def backfill(limit: int = BACKFILL_SCANS_PER_TICK) -> dict:
    scans = 0
    rows = 0
    with get_sync_session() as session:
        pending = web_hygiene.pending_scans(session, limit=limit)
        for scan_id in pending:
            rows += web_hygiene.backfill_scan(session, scan_id)
            scans += 1
            target = session.execute(
                select(Scan.target_id).where(Scan.id == scan_id)
            ).scalar_one_or_none()
            if target is not None:
                bump_sync([target])
    if scans:
        logger.info("hygiene backfill", scans=scans, rows=rows)
    return {"scans": scans, "rows": rows, "more": len(pending) >= limit}
