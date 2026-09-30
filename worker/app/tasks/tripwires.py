"""Tripwires: checked as results land, when a run settles, and on the runs they start."""

from __future__ import annotations

import uuid
from datetime import timedelta
from functools import partial

from celery import shared_task
from sqlalchemy import delete

from app.database import get_sync_session
from shared.definitions.tripwires import QUIET_RETENTION_DAYS, TRIPWIRE_KEY, CheckStatus
from shared.enums.scan import SCAN_TERMINAL_STATUSES, ScanScope, ScanStatus
from shared.logging import get_logger
from shared.models.scan import Scan
from shared.models.tripwire import TripwireRun
from shared.services.tripwires import check_scan
from shared.services.tripwires.actions import run_actions, settle_run
from shared.utils.datetime import utc_now

logger = get_logger(__name__)


def _own_run(scan: Scan) -> bool:
    return bool((scan.execution_config or {}).get(TRIPWIRE_KEY))


@shared_task(name="app.tasks.tripwires.settle")
def settle(scan_id: str) -> dict:
    """A settled run: every applicable tripwire once, or the result of a run a tripwire started."""
    with get_sync_session() as session:
        scan = session.get(Scan, uuid.UUID(scan_id))
        if scan is None or scan.status not in SCAN_TERMINAL_STATUSES:
            return {"skipped": "not settled"}
        if _own_run(scan):
            outcome = settle_run(session, scan)
            return {"result": outcome.detail if outcome else None}
        if scan.scope != ScanScope.FULL.value:
            return {"skipped": "focused"}
        runs = check_scan(session, scan, act=run_actions)
    fired = sum(1 for r in runs if r.status == CheckStatus.FIRED.value)
    logger.info("tripwires checked", scan=scan_id, checked=len(runs), fired=fired)
    return {"checked": len(runs), "fired": fired}


@shared_task(name="app.tasks.tripwires.live")
def live(scan_id: str, dimension: str) -> dict:
    """A running census scan: the tripwires that watch it as results land."""
    with get_sync_session() as session:
        scan = session.get(Scan, uuid.UUID(scan_id))
        if scan is None or scan.status != ScanStatus.RUNNING.value:
            return {"skipped": "not running"}
        if scan.scope != ScanScope.FULL.value or _own_run(scan):
            return {"skipped": "focused"}
        runs = check_scan(
            session,
            scan,
            live_dimension=dimension,
            act=partial(run_actions, live=True),
        )
    fired = sum(1 for r in runs if r.status == CheckStatus.FIRED.value)
    return {"checked": len(runs), "fired": fired, "live": True}


@shared_task(name="app.tasks.tripwires.prune")
def prune() -> dict:
    """Checks that fired nothing are kept for the retention window."""
    cutoff = utc_now() - timedelta(days=QUIET_RETENTION_DAYS)
    with get_sync_session() as session:
        removed = session.execute(
            delete(TripwireRun).where(
                TripwireRun.status != CheckStatus.FIRED.value,
                TripwireRun.checked_at < cutoff,
            )
        ).rowcount
        session.commit()
    return {"removed": int(removed or 0)}
