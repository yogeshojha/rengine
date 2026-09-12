"""Software components read from responses stored before the column existed."""

from __future__ import annotations

from celery import shared_task
from sqlalchemy import select

from app.database import get_sync_session
from shared.logging import get_logger
from shared.models.scan import Scan
from shared.services import software_match
from shared.services.asset_query.lead_cache import bump_sync

logger = get_logger(__name__)


@shared_task(name="app.tasks.software.backfill", max_retries=0)
def backfill(limit: int = software_match.BACKFILL_SCANS_PER_TICK) -> dict:
    scans = 0
    rows = 0
    with get_sync_session() as session:
        pending = software_match.pending_scans(session, limit=limit)
        for scan_id in pending:
            rows += software_match.backfill_scan(session, scan_id)
            scan = session.execute(
                select(Scan.target_id, Scan.project_id).where(Scan.id == scan_id)
            ).one_or_none()
            if scan is None:
                continue
            software_match.match_scan(
                session,
                scan_id=scan_id,
                target_id=scan.target_id,
                project_id=scan.project_id,
            )
            bump_sync([scan.target_id])
            scans += 1
    if scans:
        logger.info("software backfill", scans=scans, rows=rows)
    return {"scans": scans, "rows": rows, "more": len(pending) >= limit}
