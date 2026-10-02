"""Evaluate a tripwire against one scan: what matched, what fired, what is recorded."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import DBAPIError

from shared.definitions.tripwires import (
    FIRST_SCAN_DETAIL,
    MAX_DIFF_ROWS,
    MAX_STORED_ROWS,
    NOT_COVERED_DETAIL,
    CheckStatus,
    FireOn,
    ScopeKind,
    Trigger,
    appears_query,
)
from shared.enums.scan import SCAN_TERMINAL_STATUSES
from shared.logging import get_logger
from shared.models.scan import Scan
from shared.models.tag import TargetTag
from shared.models.target import TargetOrganization
from shared.models.tripwire import FiredRow, Tripwire, TripwireMark, TripwireRun
from shared.services.asset_query import QueryScope, QuerySyntaxError
from shared.services.asset_query.errors import NO_JIT, query_error_for
from shared.services.locks import tripwire_check
from shared.services.scan_deltas import TABLES
from shared.services.scan_scope import census_only, covers
from shared.services.surface_query import for_dimension
from shared.services.tripwires.identity import identity
from shared.utils.datetime import utc_now

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = get_logger(__name__)

EVAL_TIMEOUT = "SET LOCAL statement_timeout = '120s'"
TOO_MANY_ROWS = f"More than {MAX_DIFF_ROWS:,} rows match. Narrow the query."


@dataclass
class Evaluation:
    status: str
    matched: int = 0
    fired: list[FiredRow] = field(default_factory=list)
    detail: str | None = None
    previous_scan_id: uuid.UUID | None = None
    capped: bool = False


def _started(scan: Scan):
    return scan.started_at or scan.created_at


def previous_scan(session: Session, scan: Scan, dimension: str) -> Scan | None:
    """The target's newest settled census run before this one that covered the dimension."""
    started = func.coalesce(Scan.started_at, Scan.created_at)
    stmt = (
        select(Scan)
        .where(
            Scan.target_id == scan.target_id,
            Scan.id != scan.id,
            census_only(),
            Scan.status.in_(SCAN_TERMINAL_STATUSES),
            started < _started(scan),
            covers(TABLES[dimension], dimension),
        )
        .order_by(started.desc())
        .limit(1)
    )
    return session.execute(stmt).scalars().first()


def covered(session: Session, scan: Scan, dimension: str) -> bool:
    return bool(
        session.scalar(
            select(covers(TABLES[dimension], dimension)).where(Scan.id == scan.id)
        )
    )


def _built(dimension: str, query: str, scan_id: uuid.UUID, project_id: uuid.UUID, now):
    q = for_dimension(dimension)
    ident = identity(dimension)
    f = q.filter_model.model_validate({"q": query or None})
    scope = QueryScope((scan_id,), project_id=project_id)
    columns = ident.columns if q.takes_source else ident.columns(None)
    built = q.filtered(scope, f, now, project_id=project_id, columns=columns)
    return q, f, scope, built


def validate_query(dimension: str, query: str) -> None:
    """Parse and compile the query as a check would. Raises QuerySyntaxError."""
    probe = uuid.uuid4()
    _built(dimension, query, probe, probe, utc_now())


def rows_of(
    session: Session,
    *,
    dimension: str,
    query: str,
    scan_id: uuid.UUID,
    project_id: uuid.UUID,
    now: datetime,
    limit: int,
) -> list[FiredRow]:
    """The rows the dimension's page would show for the query, in its order."""
    q, f, scope, built = _built(dimension, query, scan_id, project_id, now)
    ident = identity(dimension)
    stmt = q.order(built, f, scope).limit(limit)
    return [
        FiredRow(
            key=ident.key(row),
            label=ident.label(row) or "",
            detail=ident.detail(row),
            severity=ident.severity(row),
            seed=ident.seed(row),
        )
        for row in session.execute(stmt)
    ]


def count_of(
    session: Session,
    *,
    dimension: str,
    query: str,
    scan_id: uuid.UUID,
    project_id: uuid.UUID,
    now: datetime,
) -> int:
    _q, _f, _scope, built = _built(dimension, query, scan_id, project_id, now)
    return int(
        session.scalar(select(func.count()).select_from(built.statement.subquery()))
        or 0
    )


def evaluate(
    session: Session,
    *,
    dimension: str,
    query: str,
    fire_on: str,
    scan: Scan,
    now: datetime,
    marks: frozenset[str] = frozenset(),
    cap: int = MAX_DIFF_ROWS,
    strict: bool = True,
) -> Evaluation:
    """Reads only. Raises QuerySyntaxError for a query the grammar refuses."""
    if not covered(session, scan, dimension):
        return Evaluation(CheckStatus.NOT_COVERED.value, detail=NOT_COVERED_DETAIL)
    previous = None
    if fire_on != FireOn.MATCHES.value:
        previous = previous_scan(session, scan, dimension)
        if previous is None:
            return Evaluation(CheckStatus.NO_BASELINE.value, detail=FIRST_SCAN_DETAIL)

    read = {
        "dimension": dimension,
        "scan_id": scan.id,
        "project_id": scan.project_id,
        "now": now,
    }
    text_query = appears_query(query) if fire_on == FireOn.APPEARS.value else query
    rows = rows_of(session, query=text_query, limit=cap + 1, **read)
    capped = len(rows) > cap
    if capped and strict:
        return Evaluation(CheckStatus.ERROR.value, detail=TOO_MANY_ROWS)
    rows = rows[:cap]

    if fire_on == FireOn.BECOMES_TRUE.value:
        before = rows_of(
            session,
            dimension=dimension,
            query=query,
            scan_id=previous.id,
            project_id=scan.project_id,
            now=now,
            limit=cap + 1,
        )
        if len(before) > cap:
            if strict:
                return Evaluation(CheckStatus.ERROR.value, detail=TOO_MANY_ROWS)
            capped = True
        held = {r.key for r in before}
        fired = [r for r in rows if r.key not in held and r.key not in marks]
        matched = len(rows)
    else:
        fired = [r for r in rows if r.key not in marks]
        matched = (
            len(rows)
            if fire_on == FireOn.MATCHES.value
            else count_of(session, query=query, **read)
        )
    status = CheckStatus.FIRED.value if fired else CheckStatus.QUIET.value
    return Evaluation(
        status,
        matched=matched,
        fired=fired,
        previous_scan_id=previous.id if previous is not None else None,
        capped=capped,
    )


# ---------- which tripwires ----------


def in_scope(
    tripwire: Tripwire,
    target_id: uuid.UUID,
    organizations: set[uuid.UUID],
    tags: set[uuid.UUID],
) -> bool:
    ids = {str(i) for i in (tripwire.scope_ids or [])}
    kind = tripwire.scope_kind
    if kind == ScopeKind.ALL.value:
        return True
    if kind == ScopeKind.TARGETS.value:
        return str(target_id) in ids
    if kind == ScopeKind.ORGANIZATION.value:
        return bool(ids & {str(o) for o in organizations})
    if kind == ScopeKind.TAG.value:
        return bool(ids & {str(t) for t in tags})
    return False


def applicable(
    session: Session, scan: Scan, *, live_dimension: str | None = None
) -> list[Tripwire]:
    """The enabled tripwires whose scope holds the scan's target."""
    stmt = select(Tripwire).where(
        Tripwire.project_id == scan.project_id, Tripwire.enabled.is_(True)
    )
    if live_dimension is not None:
        stmt = stmt.where(
            Tripwire.trigger == Trigger.SCAN_LIVE.value,
            Tripwire.dimension == live_dimension,
        )
    rows = session.execute(stmt.order_by(Tripwire.created_at)).scalars().all()
    if not rows:
        return []
    organizations = set(
        session.scalars(
            select(TargetOrganization.organization_id).where(
                TargetOrganization.target_id == scan.target_id
            )
        )
    )
    tags = set(
        session.scalars(
            select(TargetTag.tag_id).where(TargetTag.target_id == scan.target_id)
        )
    )
    return [t for t in rows if in_scope(t, scan.target_id, organizations, tags)]


# ---------- one check, recorded ----------


def _marks(
    session: Session, tripwire_id: uuid.UUID, scan_id: uuid.UUID
) -> frozenset[str]:
    return frozenset(
        session.scalars(
            select(TripwireMark.key).where(
                TripwireMark.tripwire_id == tripwire_id, TripwireMark.scan_id == scan_id
            )
        )
    )


def _mark(session: Session, tripwire_id, scan_id, rows: list[FiredRow], now) -> None:
    if not rows:
        return
    stmt = pg_insert(TripwireMark).values(
        [
            {
                "tripwire_id": tripwire_id,
                "scan_id": scan_id,
                "key": row.key[:600],
                "marked_at": now,
            }
            for row in rows
        ]
    )
    session.execute(stmt.on_conflict_do_nothing())


def _run_row(session: Session, tripwire: Tripwire, scan: Scan) -> TripwireRun:
    run = session.execute(
        select(TripwireRun)
        .where(TripwireRun.tripwire_id == tripwire.id, TripwireRun.scan_id == scan.id)
        .with_for_update()
    ).scalar_one_or_none()
    if run is None:
        run = TripwireRun(
            tripwire_id=tripwire.id,
            project_id=scan.project_id,
            target_id=scan.target_id,
            scan_id=scan.id,
            status=CheckStatus.QUIET.value,
        )
        session.add(run)
    return run


def check(
    session: Session,
    tripwire: Tripwire,
    scan: Scan,
    *,
    now: datetime | None = None,
    act=None,
) -> TripwireRun:
    """Evaluate, record the check and run the actions on what fired. Commits."""
    now = now or utc_now()
    session.execute(
        text("SELECT pg_advisory_xact_lock(:key)"),
        {"key": tripwire_check(tripwire.id, scan.id)},
    )
    session.execute(text(EVAL_TIMEOUT))
    session.execute(text(NO_JIT))
    marks = _marks(session, tripwire.id, scan.id)
    try:
        result = evaluate(
            session,
            dimension=tripwire.dimension,
            query=tripwire.query,
            fire_on=tripwire.fire_on,
            scan=scan,
            now=now,
            marks=marks,
        )
    except QuerySyntaxError as exc:
        result = Evaluation(CheckStatus.ERROR.value, detail=exc.message)
    except DBAPIError as exc:
        session.rollback()
        rejected = query_error_for(exc)
        if rejected is None:
            raise
        result = Evaluation(CheckStatus.ERROR.value, detail=rejected.message)

    run = _run_row(session, tripwire, scan)
    was_fired = run.status == CheckStatus.FIRED.value
    run.matched = result.matched
    run.checked_at = now
    if result.fired:
        run.fired += len(result.fired)
        run.rows = (list(run.rows or []) + [r.model_dump() for r in result.fired])[
            :MAX_STORED_ROWS
        ]
        run.status = CheckStatus.FIRED.value
        run.detail = None
        run.fired_at = run.fired_at or now
        _mark(session, tripwire.id, scan.id, result.fired, now)
    elif not was_fired:
        run.status = result.status
        run.detail = result.detail
    tripwire.last_checked_at = now
    if result.fired:
        tripwire.last_fired_at = now
        if not was_fired:
            tripwire.fired_count += 1
    session.flush()
    if result.fired and act is not None:
        outcomes = act(session, tripwire, run, scan, result.fired)
        run.outcomes = list(run.outcomes or []) + [
            o.model_dump(mode="json") for o in outcomes
        ]
    session.commit()
    return run


def check_scan(
    session: Session,
    scan: Scan,
    *,
    live_dimension: str | None = None,
    act=None,
) -> list[TripwireRun]:
    """Every applicable tripwire, each recorded on its own."""
    runs: list[TripwireRun] = []
    for tripwire in applicable(session, scan, live_dimension=live_dimension):
        try:
            runs.append(check(session, tripwire, scan, act=act))
        except Exception:
            session.rollback()
            logger.warning(
                "tripwire check failed",
                tripwire=str(tripwire.id),
                scan=str(scan.id),
                exc_info=True,
            )
    return runs


__all__ = [
    "Evaluation",
    "applicable",
    "check",
    "check_scan",
    "count_of",
    "covered",
    "evaluate",
    "in_scope",
    "previous_scan",
    "rows_of",
    "validate_query",
]
