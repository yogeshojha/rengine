"""Infostealer lookups for domain and URL targets."""

import time

from sqlalchemy import select

from app.celery import celery_app
from app.database import get_sync_session
from shared.definitions.infostealer import (
    LOOKUP_BATCH,
    LOOKUPS_OFF_REASON,
    NOT_APPLICABLE_REASON,
    RATE_LIMIT_PAUSE,
    REQUEST_SPACING,
)
from shared.enums.target import ENRICHMENT_FAILED
from shared.enums.task_status import TaskStatus
from shared.logging import get_logger
from shared.models.target import Target
from shared.services import infostealer
from shared.services.asset_query.lead_cache import bump_sync
from shared.services.celery_dispatch import dispatch_daily_tripwires
from shared.services.locks import LEAK_SWEEP, sync_lock
from shared.services.tripwires.daily import mark_checked, watched_targets
from tools.hudsonrock.client import (
    HudsonRockClient,
    HudsonRockError,
    HudsonRockRateLimitedError,
)

logger = get_logger(__name__)


OK, FAILED, RATE_LIMITED = "success", "failed", "rate_limited"


def _failed(targets: list[Target], error: str, *, keep_stored: bool = False) -> None:
    if keep_stored:
        return
    for target in targets:
        infostealer.mark(target, TaskStatus.FAILED, error)


def _resolve(
    session,
    client: HudsonRockClient,
    domain: str,
    targets: list[Target],
    *,
    keep_stored: bool = False,
) -> tuple[str, int]:
    """The outcome and how many of the targets gained something."""
    try:
        report = client.search_domain(domain)
    except HudsonRockError as exc:
        logger.warning("infostealer lookup failed", domain=domain, error=str(exc))
        _failed(targets, str(exc), keep_stored=keep_stored)
        session.commit()
        limited = isinstance(exc, HudsonRockRateLimitedError)
        return (RATE_LIMITED if limited else FAILED), 0
    except Exception:
        logger.exception("infostealer lookup failed", domain=domain)
        session.rollback()
        _failed(targets, ENRICHMENT_FAILED, keep_stored=keep_stored)
        session.commit()
        return FAILED, 0
    changed = 0
    for target in targets:
        if infostealer.store(session, target.id, report) is not None:
            changed += 1
        infostealer.mark(target, TaskStatus.SUCCESS)
    session.commit()
    return OK, changed


def _look_up(session, targets: list[Target], *, sweep: bool = False) -> dict:
    counts = {"success": 0, "failed": 0, "skipped": 0, "changed": 0, "limited": False}
    groups, none = infostealer.group_by_domain(targets)
    for target in none:
        infostealer.mark(target, TaskStatus.NOT_APPLICABLE, NOT_APPLICABLE_REASON)
    if not sweep:
        for group in groups.values():
            for target in group:
                infostealer.mark(target, TaskStatus.QUERYING)
    session.commit()
    counts["skipped"] = len(none)

    client = HudsonRockClient()
    paused = False
    done: list[Target] = []
    try:
        for index, (domain, group) in enumerate(groups.items()):
            if index:
                time.sleep(REQUEST_SPACING)
            outcome, changed = _resolve(
                session, client, domain, group, keep_stored=sweep
            )
            if outcome == RATE_LIMITED and sweep and not paused:
                paused = True
                time.sleep(RATE_LIMIT_PAUSE)
                outcome, changed = _resolve(
                    session, client, domain, group, keep_stored=sweep
                )
            done += group
            counts["success" if outcome == OK else "failed"] += len(group)
            counts["changed"] += changed
            if outcome == RATE_LIMITED and sweep:
                counts["limited"] = True
                break
    finally:
        stuck = [
            t
            for g in groups.values()
            for t in g
            if t.infostealer_status == TaskStatus.QUERYING
        ]
        if stuck:
            session.rollback()
            _failed(stuck, ENRICHMENT_FAILED)
            session.commit()
        bump_sync(t.id for t in done)
    if counts["changed"]:
        try:
            dispatch_daily_tripwires()
        except Exception:
            logger.warning("daily tripwires not dispatched", exc_info=True)
    return counts


@celery_app.task(
    name="app.tasks.infostealer.perform_infostealer_lookups",
    max_retries=0,
    soft_time_limit=900,
    time_limit=1200,
)
def perform_infostealer_lookups(target_ids: list[str]) -> dict:
    """Look up a batch of targets, one request per registrable domain."""
    if not target_ids:
        return {"success": 0, "failed": 0, "skipped": 0}

    with get_sync_session() as session:
        targets = list(
            session.scalars(select(Target).where(Target.id.in_(target_ids))).all()
        )
        if not infostealer.lookups_enabled(session):
            for target in targets:
                infostealer.mark(target, TaskStatus.SKIPPED, LOOKUPS_OFF_REASON)
            session.commit()
            return {"success": 0, "failed": 0, "skipped": len(targets)}
        return _look_up(session, targets)


def sweep() -> dict:
    """Read again the report of every target a daily tripwire watches."""
    from app.tasks.tripwires import daily  # noqa: PLC0415

    totals = {"targets": 0, "success": 0, "failed": 0, "changed": 0}
    with get_sync_session() as session, sync_lock(session, LEAK_SWEEP) as held:
        if not held:
            return {"skipped": "running"}
        if not infostealer.lookups_enabled(session):
            return {"skipped": "off"}
        watched = watched_targets(session)
        if not watched:
            return {"skipped": "no tripwire"}
        targets = [
            t
            for t in session.scalars(select(Target).where(Target.id.in_(watched)))
            if infostealer.lookup_domain(t.target_value, t.target_type) is not None
            and infostealer.due(infostealer.stored(session, t.id))
        ]
        totals["targets"] = len(targets)
        for start in range(0, len(targets), LOOKUP_BATCH):
            counts = _look_up(
                session, targets[start : start + LOOKUP_BATCH], sweep=True
            )
            for key in ("success", "failed", "changed"):
                totals[key] += counts[key]
            if counts["limited"]:
                totals["limited"] = True
                break
        mark_checked(session)
    totals["tripwires"] = daily()
    return totals
