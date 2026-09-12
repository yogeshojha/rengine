"""Refresh the bug bounty program list and every program's structured scope."""

from celery import shared_task
from sqlalchemy import select, text
from sqlmodel import col

from app.config import settings
from app.database import get_sync_session
from shared.definitions.bounty_feed import FEEDS_BY_PLATFORM
from shared.definitions.bounty_programs import (
    BountyPlatform,
    ProgramSource,
    ScopeAccess,
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
    sync_platform,
)
from shared.services.bounty_programs import (
    mark_synced,
    scopes_to_refresh,
    sync_due,
    sync_programs,
    sync_scopes,
)
from shared.services.bounty_providers import (
    BountyProvider,
    BountyProviderError,
    CredentialsError,
    configured_providers,
    provider_for,
)
from shared.services.celery_dispatch import dispatch_watch_reconcile
from shared.services.locks import BOUNTY_FEED, bounty_platform, sync_lock
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


def _sync_platform(session, provider: BountyProvider, *, scopes: bool) -> dict:
    """One platform's programs, then the scope of every program that moved."""
    try:
        result = sync_programs(session, provider)
    except BountyProviderError as exc:
        logger.warning(
            "bounty program sync failed", platform=provider.platform, error=str(exc)
        )
        return {"platform": provider.platform, "error": str(exc)}
    if not scopes:
        return result

    assets = 0
    failed = 0
    denied = 0
    for program in scopes_to_refresh(session, provider):
        try:
            assets += sync_scopes(session, program, provider)
            denied += program.scope_access == ScopeAccess.DENIED.value
        except CredentialsError as exc:
            logger.warning(
                "bounty scope sync rejected",
                platform=provider.platform,
                error=str(exc),
            )
            break
        except BountyProviderError as exc:
            failed += 1
            logger.info(
                "bounty scope sync failed",
                platform=provider.platform,
                handle=program.handle,
                error=str(exc),
            )
            if failed >= SCOPE_FAILURE_BUDGET:
                logger.warning(
                    "bounty scope sync abandoned",
                    platform=provider.platform,
                    failed=failed,
                )
                break
    return {
        **result,
        "assets": assets,
        "scope_failures": failed,
        "scope_denied": denied,
    }


@shared_task(name="app.tasks.bounty_programs.sync")
def sync(scopes: bool = True, force: bool = True, platform: str | None = None) -> dict:
    """Pull programs, then each program's scope, for every connected platform."""
    started = utc_now()
    with get_sync_session() as session:
        if not force and not sync_due(session):
            return {"skipped": "not_due"}
        providers = (
            [p for p in [provider_for(session, platform)] if p]
            if platform
            else configured_providers(session)
        )
        if not providers:
            logger.info("bounty program sync skipped, no platform credentials")
            return {"skipped": "not_configured"}

        results = []
        for provider in providers:
            with sync_lock(session, bounty_platform(provider.platform)) as held:
                if not held:
                    results.append(
                        {"platform": provider.platform, "skipped": "already_running"}
                    )
                    continue
                results.append(_sync_platform(session, provider, scopes=scopes))

        mark_synced(session)
        alerted = _notify(session, started)
        if scopes:
            dispatch_watch_reconcile()
        return {"platforms": results, "alerted": alerted}


@shared_task(name="app.tasks.bounty_programs.sync_program")
def sync_program(handle: str, platform: str = BountyPlatform.HACKERONE.value) -> dict:
    """Refresh one program's scope, for a program opened before the sweep reached it."""
    with get_sync_session() as session:
        program = session.execute(
            select(BountyProgram).where(
                BountyProgram.platform == platform,
                BountyProgram.handle == handle,
            )
        ).scalar_one_or_none()
        if not program:
            return {"error": "unknown program"}
        feed = program.source == ProgramSource.FEED.value
        key = BOUNTY_FEED if feed else bounty_platform(platform)
        with sync_lock(session, key) as held:
            if not held:
                return {"skipped": "already_running"}
            if feed:
                spec = FEEDS_BY_PLATFORM.get(platform)
                return (
                    sync_platform(session, spec)
                    if spec
                    else {"error": "unknown platform"}
                )
            provider = provider_for(session, platform)
            if not provider:
                return {"skipped": "not_configured"}
            try:
                return {"assets": sync_scopes(session, program, provider)}
            except BountyProviderError as exc:
                logger.info(
                    "bounty scope sync failed",
                    platform=platform,
                    handle=handle,
                    error=str(exc),
                )
                return {"error": str(exc)}


@shared_task(name="app.tasks.bounty_programs.sync_feed")
def sync_feed(force: bool = True) -> dict:
    """Public scope for the platforms with no researcher API."""
    started = utc_now()
    with get_sync_session() as session, sync_lock(session, BOUNTY_FEED) as held:
        if not held:
            return {"skipped": "already_running"}
        if not force and not feed_due(session):
            return {"skipped": "not_due"}
        result = sync_feeds(session)
        if result["platforms"]:
            mark_feed_synced(session)
            dispatch_watch_reconcile()
        return {**result, "alerted": _notify(session, started)}
