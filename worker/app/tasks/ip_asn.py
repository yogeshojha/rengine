"""Weekly refresh of the IP -> ASN / country range tables."""

from celery import shared_task

from app.database import get_sync_session
from shared.logging import get_logger
from shared.services.ip_asn import sync_ranges

logger = get_logger(__name__)


@shared_task(name="app.tasks.ip_asn.refresh")
def refresh() -> dict:
    with get_sync_session() as session:
        counts = sync_ranges(session)
    logger.info("ip range tables refreshed", **counts)
    return counts
