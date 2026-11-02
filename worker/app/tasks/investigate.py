"""Investigate: settle a plan's focused run when it finishes."""

from __future__ import annotations

import uuid

from celery import shared_task

from app.database import get_sync_session
from shared.enums.scan import SCAN_TERMINAL_STATUSES, ScanStatus
from shared.logging import get_logger
from shared.models.scan import Scan
from shared.services.investigate import replay_known_exploited
from shared.services.investigate import settle as settle_plan

logger = get_logger(__name__)


@shared_task(name="app.tasks.investigate.settle")
def settle(scan_id: str) -> dict:
    """A launched run has settled: read its result onto the plan and the verdict."""
    with get_sync_session() as session:
        scan = session.get(Scan, uuid.UUID(scan_id))
        if scan is None or scan.status not in SCAN_TERMINAL_STATUSES:
            return {"skipped": "not settled"}
        settled = settle_plan(session, scan)
        session.commit()
    logger.info("investigate settle", scan=scan_id, settled=settled)
    return {"settled": settled}


@shared_task(name="app.tasks.investigate.replay_kev")
def replay_kev(scan_id: str) -> dict:
    """A census run completed: replay its known-exploited findings when the rule is on."""
    with get_sync_session() as session:
        scan = session.get(Scan, uuid.UUID(scan_id))
        if scan is None or scan.status != ScanStatus.COMPLETED.value:
            return {"skipped": "not completed"}
        started = replay_known_exploited(session, scan)
    return {"started": started}
