"""Source IP checks at the start and end of a scan run."""

import uuid

from app.celery import celery_app
from app.database import get_sync_session
from app.orchestrator.stage import load_resolved
from shared.definitions.source_ip import SourceIpFailure
from shared.logging import get_logger
from shared.models.scan import Scan
from shared.services import source_ip
from shared.utils.datetime import utc_now

logger = get_logger(__name__)

CHECK_SOFT_LIMIT = 30
CHECK_HARD_LIMIT = 60


def _proxy_of(scan: Scan) -> tuple[str | None, SourceIpFailure | None]:
    try:
        return load_resolved(scan.execution_config).proxy_url or None, None
    except Exception:
        logger.warning(
            "source ip check could not read the run's proxy", scan=str(scan.id)
        )
        return None, SourceIpFailure.PROXY_UNREADABLE


@celery_app.task(
    name="app.tasks.source_ip.check",
    max_retries=0,
    soft_time_limit=CHECK_SOFT_LIMIT,
    time_limit=CHECK_HARD_LIMIT,
)
def check(scan_id: str, phase: str) -> dict:
    """Record the address this run's traffic leaves from, through its own proxy."""
    with get_sync_session() as session:
        scan = session.get(Scan, uuid.UUID(scan_id))
        if scan is None:
            return {"skipped": "scan not found"}
        if not source_ip.wants_check(scan.source_ip, phase):
            return {"skipped": "not wanted"}
        if not source_ip.lookups_enabled(session):
            return {"skipped": "lookups off"}
        proxy, unreadable = _proxy_of(scan)
        session.rollback()

    result = {"failure": unreadable.value} if unreadable else source_ip.lookup(proxy)

    with get_sync_session() as session:
        scan = session.get(Scan, uuid.UUID(scan_id), with_for_update=True)
        if scan is None:
            session.commit()
            return {"skipped": "scan not found"}
        scan.source_ip = source_ip.record(
            scan.source_ip,
            phase,
            result,
            proxied=proxy is not None or unreadable is not None,
            at=utc_now(),
        )
        session.commit()
    return {"phase": phase, "failure": result.get("failure")}
