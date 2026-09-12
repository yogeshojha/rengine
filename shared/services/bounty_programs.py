"""Program libraries from the platforms with a researcher API: sync, events and settings."""

from __future__ import annotations

import time
from datetime import datetime, timedelta

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from shared.definitions.bounty_programs import (
    DEFAULT_SYNC_INTERVAL,
    MAX_EVENT_DETAIL,
    SYNC_INTERVAL_HOURS,
    BountyEvent,
    ScopeAccess,
    ScopeState,
    SubmissionState,
    asset_type_spec,
)
from shared.logging import get_logger
from shared.models.bounty_program import BountyEventRow, BountyProgram, BountyScope
from shared.services.bounty_providers import AccessDeniedError, BountyProvider
from shared.utils.datetime import utc_now

logger = get_logger(__name__)


def event_row(program: BountyProgram, kind: str, **extra) -> BountyEventRow:
    return BountyEventRow(
        platform=program.platform,
        program_id=program.id,
        handle=program.handle,
        program_name=program.name,
        kind=kind,
        **extra,
    )


def _program_changes(current: BountyProgram, row: dict) -> list[str]:
    """What moved on a program the library already knew about."""
    kinds: list[str] = []
    if current.submission_state != row["submission_state"]:
        kinds.append(
            BountyEvent.SUBMISSIONS_OPENED.value
            if row["submission_state"] == SubmissionState.OPEN.value
            else BountyEvent.SUBMISSIONS_CLOSED.value
        )
    if (
        current.program_state != row["program_state"]
        and row["program_state"] == "public"
    ):
        kinds.append(BountyEvent.PROGRAM_WENT_PUBLIC.value)
    if row["offers_bounties"] and not current.offers_bounties:
        kinds.append(BountyEvent.BOUNTIES_STARTED.value)
    return kinds


def sync_programs(session: Session, provider: BountyProvider) -> dict[str, int]:
    """Refresh one platform's program list."""
    started = time.monotonic()
    rows = provider.programs()
    existing = {
        p.handle: p
        for p in session.execute(
            select(BountyProgram).where(BountyProgram.platform == provider.platform)
        ).scalars()
    }
    baseline = bool(existing)
    created = updated = 0
    seen: set[str] = set()
    events: list[BountyEventRow] = []
    for row in rows:
        handle = row.get("handle")
        if not handle or handle in seen:
            continue
        seen.add(handle)
        current = existing.get(handle)
        row["sources"] = sorted({*(current.sources if current else []), row["source"]})
        if current is None:
            program = BountyProgram(**row)
            session.add(program)
            session.flush()
            created += 1
            if baseline:
                events.append(event_row(program, BountyEvent.PROGRAM_ADDED.value))
            continue
        for kind in _program_changes(current, row):
            events.append(event_row(current, kind))
        if current.source != row["source"]:
            current.scopes_synced_at = None
            current.scope_access = None
        for key, value in row.items():
            setattr(current, key, value)
        updated += 1
    session.add_all(events)
    session.commit()
    return {
        "platform": provider.platform,
        "programs": len(seen),
        "created": created,
        "updated": updated,
        "duration_ms": int((time.monotonic() - started) * 1000),
        "events": len(events),
    }


_SCOPE_TRANSITIONS = {
    (ScopeState.IN_SCOPE.value, ScopeState.OUT_OF_SCOPE.value): (
        BountyEvent.WENT_OUT_OF_SCOPE.value
    ),
    (ScopeState.OUT_OF_SCOPE.value, ScopeState.IN_SCOPE.value): (
        BountyEvent.CAME_INTO_SCOPE.value
    ),
}


def scope_changes(
    program: BountyProgram, before: dict[tuple[str, str], str], after: dict
) -> list[BountyEventRow]:
    """Added, removed and flipped assets, never on a program's first read."""
    events: list[BountyEventRow] = []
    for key, row in after.items():
        asset_type, identifier = key
        was = before.get(key)
        if was is None:
            kind = BountyEvent.SCOPE_ADDED.value
        else:
            kind = _SCOPE_TRANSITIONS.get((was, row["scope_state"]))
            if kind is None:
                continue
        events.append(
            event_row(
                program,
                kind,
                asset_type=asset_type,
                asset_identifier=identifier,
                detail=(row.get("instruction") or None)
                and row["instruction"][:MAX_EVENT_DETAIL],
            )
        )
    for key in before.keys() - after.keys():
        events.append(
            event_row(
                program,
                BountyEvent.SCOPE_REMOVED.value,
                asset_type=key[0],
                asset_identifier=key[1],
            )
        )
    return events


def sync_scopes(
    session: Session, program: BountyProgram, provider: BountyProvider
) -> int:
    """Replace one program's scope rows with what the platform reports now."""
    try:
        fetched = provider.scopes(program)
    except AccessDeniedError:
        logger.info(
            "bounty scope refused",
            platform=provider.platform,
            handle=program.handle,
        )
        program.scope_access = ScopeAccess.DENIED.value
        program.joined = False
        session.commit()
        return 0
    deduped: dict[tuple[str, str], dict] = {}
    for row in fetched.entries:
        deduped[(row["asset_type"], row["asset_identifier"])] = {
            **row,
            "program_id": program.id,
        }

    before: dict[tuple[str, str], str] = {}
    if program.scopes_synced_at is not None:
        before = {
            (s.asset_type, s.asset_identifier): s.scope_state
            for s in session.execute(
                select(BountyScope).where(BountyScope.program_id == program.id)
            ).scalars()
        }
        session.add_all(scope_changes(program, before, deduped))

    session.execute(delete(BountyScope).where(BountyScope.program_id == program.id))
    session.add_all([BountyScope(**row) for row in deduped.values()])
    for key, value in fetched.program_updates.items():
        setattr(program, key, value)
    program.scope_access = None
    program.scopes_synced_at = utc_now()
    session.commit()
    return len(deduped)


def scopes_to_refresh(
    session: Session, provider: BountyProvider
) -> list[BountyProgram]:
    """Every program whose scope this sync must read, narrowed by the platform's own feed."""
    programs = list(
        session.execute(
            select(BountyProgram).where(BountyProgram.platform == provider.platform)
        )
        .scalars()
        .all()
    )
    denied = ScopeAccess.DENIED.value
    read_at = [p.scopes_synced_at for p in programs if p.scopes_synced_at is not None]
    unread = [
        p for p in programs if p.scopes_synced_at is None and p.scope_access != denied
    ]
    if unread or not read_at:
        return programs
    oldest = min(read_at)
    try:
        changed = provider.changed_since(oldest)
    except Exception as exc:
        logger.info(
            "bounty scope change feed unavailable",
            platform=provider.platform,
            error=str(exc),
        )
        return programs
    if changed is None:
        return programs
    return [
        p
        for p in programs
        if not p.external_id or p.external_id in changed or p.scope_access == denied
    ]


def sync_settings(session: Session) -> tuple[str, datetime | None]:
    row = session.execute(
        text(
            "SELECT bounty_sync_interval, bounty_synced_at FROM instance_settings LIMIT 1"
        )
    ).first()
    if not row:
        return DEFAULT_SYNC_INTERVAL, None
    return (row[0] or DEFAULT_SYNC_INTERVAL), row[1]


def sync_due(session: Session) -> bool:
    """Whether the schedule says to sync now."""
    interval, last = sync_settings(session)
    hours = SYNC_INTERVAL_HOURS.get(interval)
    if hours is None:
        return False
    return last is None or (utc_now() - last) >= timedelta(hours=hours)


def mark_synced(session: Session) -> None:
    session.execute(text("UPDATE instance_settings SET bounty_synced_at = now()"))
    session.commit()


def unreachable_summary(scopes: list[BountyScope]) -> dict[str, int]:
    """What the program lists that no scan can reach, counted by asset type label."""
    counts: dict[str, int] = {}
    for scope in scopes:
        if scope.target_value:
            continue
        label = asset_type_spec(scope.asset_type).label
        counts[label] = counts.get(label, 0) + 1
    return counts
