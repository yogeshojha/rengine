"""Daily tripwires: checked against what a lookup added, with no scan."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import select, text

from shared.definitions.infostealer import ANY, AUDIENCE_LABELS, Audience
from shared.definitions.tripwires import (
    AUDIENCE_PARAM,
    DAILY_QUIET_DETAIL,
    MAX_STORED_ROWS,
    CheckStatus,
    ScopeKind,
    Source,
    Trigger,
)
from shared.logging import get_logger
from shared.models.infostealer import InfostealerChange
from shared.models.tag import TargetTag
from shared.models.target import Target, TargetOrganization
from shared.models.tripwire import FiredRow, Tripwire, TripwireRun
from shared.services.locks import tripwire_check
from shared.services.tripwires.evaluate import _record_outcomes, in_scope
from shared.utils.datetime import utc_now
from shared.utils.text import counted

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = get_logger(__name__)

PENDING_BATCH = 500
EMPLOYEES_KEY = "employees"
USERS_KEY = "users"
COUNT_LABELS: dict[str, str] = {
    EMPLOYEES_KEY: "Compromised employees",
    USERS_KEY: "Compromised users",
}


def _audiences(params: dict | None) -> tuple[str, ...]:
    chosen = (params or {}).get(AUDIENCE_PARAM, ANY)
    if chosen == ANY:
        return (Audience.EMPLOYEE.value, Audience.USER.value)
    return (chosen,)


def _host_row(entry: dict) -> FiredRow:
    audience = AUDIENCE_LABELS.get(entry["audience"], entry["audience"])
    before, after = int(entry["credentials_from"]), int(entry["credentials_to"])
    detail = (
        f"{audience} · {counted(after, 'credential')} · first listed"
        if entry.get("new")
        else f"{audience} · {before:,} to {counted(after, 'credential')}"
    )
    return FiredRow(
        key=f"{entry['audience']}|{entry['host']}",
        label=entry["host"],
        detail=detail,
        seed=entry["host"],
    )


def rows_of(change: InfostealerChange, params: dict | None = None) -> list[FiredRow]:
    """The change as rows, counts first, narrowed to the chosen audience."""
    audiences = _audiences(params)
    rows: list[FiredRow] = []
    counts = (
        (
            Audience.EMPLOYEE.value,
            EMPLOYEES_KEY,
            change.employees_from,
            change.employees_to,
        ),
        (Audience.USER.value, USERS_KEY, change.users_from, change.users_to),
    )
    for audience, key, before, after in counts:
        if audience in audiences and after > before:
            rows.append(
                FiredRow(
                    key=key, label=COUNT_LABELS[key], detail=f"{before:,} to {after:,}"
                )
            )
    rows += [
        _host_row(entry)
        for entry in change.hosts or []
        if entry.get("audience") in audiences
    ]
    return rows


def rise(change: InfostealerChange, params: dict | None = None) -> tuple[int, int]:
    """New compromised employees and users inside the chosen audience."""
    audiences = _audiences(params)
    employees = change.employees_to - change.employees_from
    users = change.users_to - change.users_from
    return (
        max(employees, 0) if Audience.EMPLOYEE.value in audiences else 0,
        max(users, 0) if Audience.USER.value in audiences else 0,
    )


# ---------- which tripwires, which targets ----------


def _memberships(
    session: Session, target_id: uuid.UUID
) -> tuple[set[uuid.UUID], set[uuid.UUID]]:
    organizations = set(
        session.scalars(
            select(TargetOrganization.organization_id).where(
                TargetOrganization.target_id == target_id
            )
        )
    )
    tags = set(
        session.scalars(
            select(TargetTag.tag_id).where(TargetTag.target_id == target_id)
        )
    )
    return organizations, tags


def watching(
    session: Session, target: Target, source: str = Source.LEAKED_LOGINS.value
) -> list[Tripwire]:
    """The enabled daily tripwires of the source whose scope holds the target."""
    rows = (
        session.execute(
            select(Tripwire)
            .where(
                Tripwire.project_id == target.project_id,
                Tripwire.enabled.is_(True),
                Tripwire.trigger == Trigger.DAILY.value,
                Tripwire.source == source,
            )
            .order_by(Tripwire.created_at)
        )
        .scalars()
        .all()
    )
    if not rows:
        return []
    organizations, tags = _memberships(session, target.id)
    return [t for t in rows if in_scope(t, target.id, organizations, tags)]


def _scoped(tripwire: Tripwire):
    ids = [uuid.UUID(str(i)) for i in tripwire.scope_ids or []]
    stmt = select(Target.id).where(Target.project_id == tripwire.project_id)
    if tripwire.scope_kind == ScopeKind.TARGETS.value:
        return stmt.where(Target.id.in_(ids))
    if tripwire.scope_kind == ScopeKind.ORGANIZATION.value:
        return stmt.where(
            Target.id.in_(
                select(TargetOrganization.target_id).where(
                    TargetOrganization.organization_id.in_(ids)
                )
            )
        )
    if tripwire.scope_kind == ScopeKind.TAG.value:
        return stmt.where(
            Target.id.in_(select(TargetTag.target_id).where(TargetTag.tag_id.in_(ids)))
        )
    return stmt


def watched_targets(
    session: Session, source: str = Source.LEAKED_LOGINS.value
) -> set[uuid.UUID]:
    """Every target an enabled daily tripwire of the source reads."""
    tripwires = session.scalars(
        select(Tripwire).where(
            Tripwire.enabled.is_(True),
            Tripwire.trigger == Trigger.DAILY.value,
            Tripwire.source == source,
        )
    ).all()
    out: set[uuid.UUID] = set()
    for tripwire in tripwires:
        out.update(session.scalars(_scoped(tripwire)))
    return out


def mark_checked(session: Session, source: str = Source.LEAKED_LOGINS.value) -> None:
    now = utc_now()
    for tripwire in session.scalars(
        select(Tripwire).where(
            Tripwire.enabled.is_(True),
            Tripwire.trigger == Trigger.DAILY.value,
            Tripwire.source == source,
        )
    ):
        tripwire.last_checked_at = now
    session.commit()


# ---------- one check, recorded ----------


def check_change(
    session: Session,
    tripwire: Tripwire,
    change: InfostealerChange,
    target: Target,
    *,
    act=None,
) -> TripwireRun:
    """Record the check of one change and run the actions on what fired. Commits."""
    now = utc_now()
    session.execute(
        text("SELECT pg_advisory_xact_lock(:key)"),
        {"key": tripwire_check(tripwire.id, change.id)},
    )
    held = session.execute(
        select(TripwireRun).where(
            TripwireRun.tripwire_id == tripwire.id, TripwireRun.event_id == change.id
        )
    ).scalar_one_or_none()
    if held is not None:
        session.commit()
        return held
    rows = rows_of(change, tripwire.params)
    run = TripwireRun(
        tripwire_id=tripwire.id,
        project_id=tripwire.project_id,
        target_id=target.id,
        event_id=change.id,
        status=CheckStatus.FIRED.value if rows else CheckStatus.QUIET.value,
        matched=len(rows_of(change)),
        fired=len(rows),
        rows=[r.model_dump() for r in rows[:MAX_STORED_ROWS]],
        detail=None if rows else DAILY_QUIET_DETAIL,
        checked_at=now,
        fired_at=now if rows else None,
    )
    session.add(run)
    tripwire.last_checked_at = now
    if rows:
        tripwire.last_fired_at = now
        tripwire.fired_count += 1
    session.flush()
    tripwire_id, change_id, run_id = tripwire.id, change.id, run.id
    session.commit()
    if rows and act is not None:
        outcomes = act(session, tripwire, run, target, change, rows)
        run = _record_outcomes(session, tripwire_id, change_id, run_id, outcomes)
    return run


def check_changes(session: Session, *, act=None) -> list[TripwireRun]:
    """Every change no tripwire has read, each tripwire recorded on its own."""
    pending = list(
        session.scalars(
            select(InfostealerChange.id)
            .where(InfostealerChange.evaluated_at.is_(None))
            .order_by(InfostealerChange.checked_at)
            .limit(PENDING_BATCH)
        )
    )
    runs: list[TripwireRun] = []
    for change_id in pending:
        change = session.get(InfostealerChange, change_id)
        target = session.get(Target, change.target_id) if change is not None else None
        if change is None or target is None:
            continue
        for tripwire_id in [t.id for t in watching(session, target)]:
            try:
                runs.append(
                    check_change(
                        session,
                        session.get(Tripwire, tripwire_id),
                        session.get(InfostealerChange, change_id),
                        session.get(Target, target.id),
                        act=act,
                    )
                )
            except Exception:
                session.rollback()
                logger.warning(
                    "daily tripwire check failed",
                    tripwire=str(tripwire_id),
                    change=str(change_id),
                    exc_info=True,
                )
        change = session.get(InfostealerChange, change_id)
        if change is not None:
            change.evaluated_at = utc_now()
            session.commit()
    return runs


__all__ = [
    "check_change",
    "check_changes",
    "mark_checked",
    "rise",
    "rows_of",
    "watched_targets",
    "watching",
]
