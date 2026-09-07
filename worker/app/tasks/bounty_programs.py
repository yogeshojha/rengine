"""Refresh the bug bounty program list and every program's structured scope."""

from celery import shared_task
from sqlalchemy import select, text
from sqlmodel import col

from app.config import settings
from app.database import get_sync_session
from shared.definitions.bounty_programs import (
    BountyPlatform,
    notify_enabled,
    notify_events,
)
from shared.definitions.notifications import BountyChange, bounty_changes
from shared.logging import get_logger
from shared.models.bounty_program import BountyEventRow, BountyProgram
from shared.services.bounty_feed import (
    feed_due,
    mark_feed_synced,
    sync_feeds,
)
from shared.services.bounty_programs import (
    CredentialsError,
    HackerOneError,
    credentials,
    mark_synced,
    sync_due,
    sync_programs,
    sync_scopes,
)
from shared.services.notification_sync import SyncNotificationPublisher
from shared.utils.datetime import utc_now

logger = get_logger(__name__)

SCOPE_FAILURE_BUDGET = 25
ALERT_LIMIT = 40


def _notify(session, since) -> int:
    """Delta-only, and only the change kinds the operator asked to hear about."""
    stored = session.execute(
        text("SELECT bounty_settings FROM instance_settings LIMIT 1")
    ).scalar_one_or_none()
    if not notify_enabled(stored):
        return 0
    kinds = notify_events(stored)
    if not kinds:
        return 0
    rows = (
        session.execute(
            select(BountyEventRow)
            .where(
                BountyEventRow.created_at >= since,
                col(BountyEventRow.kind).in_(sorted(kinds)),
            )
            .order_by(BountyEventRow.created_at.desc())
            .limit(ALERT_LIMIT)
        )
        .scalars()
        .all()
    )
    payload = bounty_changes(
        [
            BountyChange(
                kind=r.kind,
                program=r.program_name,
                handle=r.handle,
                asset=r.asset_identifier,
            )
            for r in rows
        ]
    )
    if payload is None:
        return 0
    try:
        SyncNotificationPublisher(settings.redis_url).publish(
            session=session,
            type=payload["type"],
            severity=payload["severity"],
            title=payload["title"],
            message=payload["message"],
            metadata=payload.get("metadata"),
        )
    except Exception:
        logger.warning("bounty change notification failed", exc_info=True)
    return len(rows)


@shared_task(name="app.tasks.bounty_programs.sync")
def sync(scopes: bool = True, force: bool = True) -> dict:
    """Pull programs, then each program's scope so the library can be filtered by it."""
    started = utc_now()
    with get_sync_session() as session:
        # a manual refresh always runs, whatever the schedule says
        if not force and not sync_due(session):
            return {"skipped": "not_due"}
        auth = credentials(session)
        if not auth:
            logger.info("bounty program sync skipped, no hackerone credentials")
            return {"skipped": "not_configured"}
        try:
            result = sync_programs(session, auth)
        except CredentialsError as exc:
            logger.warning("bounty program sync rejected", error=str(exc))
            return {"error": str(exc)}
        except HackerOneError as exc:
            logger.warning("bounty program sync failed", error=str(exc))
            return {"error": str(exc)}

        if not scopes:
            mark_synced(session)
            return {**result, "alerted": _notify(session, started)}

        programs = (
            session.execute(
                select(BountyProgram).where(
                    BountyProgram.platform == BountyPlatform.HACKERONE.value
                )
            )
            .scalars()
            .all()
        )
        assets = 0
        failed = 0
        for program in programs:
            try:
                assets += sync_scopes(session, program, auth)
            except CredentialsError as exc:
                logger.warning("bounty scope sync rejected", error=str(exc))
                break
            except HackerOneError as exc:
                failed += 1
                logger.info(
                    "bounty scope sync failed", handle=program.handle, error=str(exc)
                )
                # a run of failures means the API is unhappy, not this one program
                if failed >= SCOPE_FAILURE_BUDGET:
                    logger.warning("bounty scope sync abandoned", failed=failed)
                    break
        mark_synced(session)
        alerted = _notify(session, started)
        return {
            **result,
            "assets": assets,
            "scope_failures": failed,
            "alerted": alerted,
        }


@shared_task(name="app.tasks.bounty_programs.sync_program")
def sync_program(handle: str) -> dict:
    """Refresh one program's scope, for a program opened before the sweep reached it."""
    with get_sync_session() as session:
        auth = credentials(session)
        if not auth:
            return {"skipped": "not_configured"}
        program = session.execute(
            select(BountyProgram).where(
                BountyProgram.platform == BountyPlatform.HACKERONE.value,
                BountyProgram.handle == handle,
            )
        ).scalar_one_or_none()
        if not program:
            return {"error": "unknown program"}
        try:
            return {"assets": sync_scopes(session, program, auth)}
        except HackerOneError as exc:
            logger.info("bounty scope sync failed", handle=handle, error=str(exc))
            return {"error": str(exc)}


@shared_task(name="app.tasks.bounty_programs.sync_feed")
def sync_feed(force: bool = True) -> dict:
    """Public scope for the platforms with no researcher API."""
    started = utc_now()
    with get_sync_session() as session:
        if not force and not feed_due(session):
            return {"skipped": "not_due"}
        result = sync_feeds(session)
        mark_feed_synced(session)
        return {**result, "alerted": _notify(session, started)}
