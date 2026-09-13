"""Weekly refresh of the IP -> ASN / country range tables."""

from celery import shared_task
from sqlalchemy import select

from app.database import get_sync_session
from shared.logging import get_logger
from shared.models.scan import Scan
from shared.services.asset_query.lead_cache import bump_sync
from shared.services.ip_asn import backfill_addresses, sync_ranges

logger = get_logger(__name__)


def _fill(session) -> dict:
    filled = backfill_addresses(session)
    if not filled.scans:
        return {"addresses_filled": 0, "hosts_filled": 0}
    targets = session.execute(
        select(Scan.target_id).where(Scan.id.in_(filled.scans)).distinct()
    ).scalars()
    bump_sync([t for t in targets if t is not None])
    return {"addresses_filled": filled.addresses, "hosts_filled": filled.hosts}


@shared_task(name="app.tasks.ip_asn.refresh")
def refresh() -> dict:
    with get_sync_session() as session:
        counts = sync_ranges(session)
        counts |= _fill(session)
    logger.info("ip range tables refreshed", **counts)
    return counts


@shared_task(name="app.tasks.ip_asn.backfill", max_retries=0)
def backfill() -> dict:
    """Fill addresses left blank by a scan that ran while the ranges were loading."""
    with get_sync_session() as session:
        counts = _fill(session)
    if counts["addresses_filled"]:
        logger.info("ip range backfill", **counts)
    return counts
