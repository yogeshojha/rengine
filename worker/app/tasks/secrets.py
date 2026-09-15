"""Mine secrets from responses stored before the stage existed."""

from __future__ import annotations

from celery import shared_task
from sqlalchemy import select

from app.database import get_sync_session
from shared.definitions.secrets import BACKFILL_SCANS_PER_TICK
from shared.logging import get_logger
from shared.models.scan import Scan
from shared.services import secret_mining
from shared.services.asset_query.lead_cache import bump_sync

logger = get_logger(__name__)


@shared_task(name="app.tasks.secrets.backfill", max_retries=0)
def backfill(limit: int = BACKFILL_SCANS_PER_TICK) -> dict:
    scans = 0
    secrets = 0
    with get_sync_session() as session:
        pending = secret_mining.pending_scans(session, limit=limit)
        for scan_id in pending:
            scan = session.execute(
                select(Scan.target_id, Scan.project_id).where(Scan.id == scan_id)
            ).one_or_none()
            if scan is None:
                continue
            outcome = secret_mining.mine_scan(
                session,
                scan_id=scan_id,
                target_id=scan.target_id,
                project_id=scan.project_id,
            )
            session.execute(
                Scan.__table__.update()
                .where(Scan.id == scan_id)
                .values(secrets_found=outcome.secrets)
            )
            session.commit()
            bump_sync([scan.target_id])
            secrets += outcome.secrets
            scans += 1
    if scans:
        logger.info("secret backfill", scans=scans, secrets=secrets)
    return {"scans": scans, "secrets": secrets, "more": len(pending) >= limit}
