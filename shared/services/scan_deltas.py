"""First-seen and retired counts per scan, stored and kept valid by revision triggers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, and_, exists, func, literal, select, tuple_
from sqlalchemy.dialects.postgresql import ARRAY, insert
from sqlalchemy.orm import aliased

from shared.definitions.compare import COMPARE_KEYS
from shared.definitions.surface import SurfaceDimension
from shared.enums.scan import SCAN_TERMINAL_STATUSES, ScanScope, ScanStatus
from shared.models.endpoint import Endpoint
from shared.models.ip_address import IpAddress
from shared.models.port import Port
from shared.models.scan import Scan
from shared.models.scan_delta import ScanDelta, ScanRetired, ScanRevision
from shared.models.secret import Secret
from shared.models.software import SoftwareCve
from shared.models.subdomain import Subdomain
from shared.models.vulnerability import Vulnerability
from shared.services.scan_scope import census_only, covers

if TYPE_CHECKING:
    from collections.abc import Iterable
    from uuid import UUID

    from sqlalchemy.orm import Session

TABLES = {
    SurfaceDimension.WEB_ASSETS.value: Subdomain,
    SurfaceDimension.ENDPOINTS.value: Endpoint,
    SurfaceDimension.SERVICES.value: Port,
    SurfaceDimension.IPS.value: IpAddress,
    SurfaceDimension.VULNERABILITIES.value: Vulnerability,
    SurfaceDimension.SOFTWARE.value: SoftwareCve,
    SurfaceDimension.SECRETS.value: Secret,
}
# a finding's first sighting depends on its triage state
FIRST_SEEN = tuple(
    key for key in TABLES if key != SurfaceDimension.VULNERABILITIES.value
)
WEB = SurfaceDimension.WEB_ASSETS.value
BACKFILL_SCANS_PER_TICK = 20

Pair = tuple["UUID", "UUID"]


@dataclass(frozen=True)
class Fill:
    """Counts computed on a read, to be stored by the caller."""

    first_seen: list[dict]
    retired: list[dict]

    def __bool__(self) -> bool:
        return bool(self.first_seen or self.retired)


def _keys(dimension: str, model):
    return [getattr(model, name) for name in COMPARE_KEYS[dimension]]


def _rev(column, scan_id, dimension: str):
    return func.coalesce(
        select(column)
        .where(ScanRevision.scan_id == scan_id, ScanRevision.dimension == dimension)
        .scalar_subquery(),
        0,
    )


def seen_earlier(dimension: str, model=None):
    """An earlier row of the same key for the row's target, from another scan."""
    model = model or TABLES[dimension]
    earlier = aliased(model)
    return exists(
        select(1).where(
            earlier.target_id == model.target_id,
            *[
                a == b
                for a, b in zip(
                    _keys(dimension, earlier), _keys(dimension, model), strict=True
                )
            ],
            earlier.scan_id != model.scan_id,
            earlier.discovered_at < model.discovered_at,
        )
    )


def _facts_statement(dimension: str, scan_id: UUID):
    model = TABLES[dimension]
    first = (
        select(func.count())
        .select_from(model)
        .where(model.scan_id == scan_id, ~seen_earlier(dimension, model))
        .scalar_subquery()
    )
    held = (
        select(func.count(), func.min(model.discovered_at))
        .where(model.scan_id == scan_id)
        .subquery()
    )
    return select(
        _rev(ScanRevision.history_rev, scan_id, dimension),
        first,
        *held.c,
    )


def _rows_statement(dimension: str, scan_ids: list[UUID]):
    model = TABLES[dimension]
    return (
        select(model.scan_id, func.count(), func.min(model.discovered_at))
        .where(model.scan_id.in_(scan_ids))
        .group_by(model.scan_id)
    )


def _retired_statement(dimension: str, scan_id: UUID, prev_id: UUID):
    model = TABLES[dimension]
    current = aliased(model)
    still_there = exists(
        select(1).where(
            current.scan_id == scan_id,
            *[
                a == b
                for a, b in zip(
                    _keys(dimension, current), _keys(dimension, model), strict=True
                )
            ],
        )
    )
    count = (
        select(func.count())
        .select_from(model)
        .where(model.scan_id == prev_id, ~still_there)
        .scalar_subquery()
    )
    return select(
        _rev(ScanRevision.rows_rev, scan_id, dimension),
        _rev(ScanRevision.rows_rev, prev_id, dimension),
        count,
    )


def _stored_facts(dimension: str, scan_ids: list[UUID], *, loose: bool):
    rev = aliased(ScanRevision)
    current = func.coalesce(rev.history_rev, 0)
    query = (
        select(
            ScanDelta.scan_id,
            ScanDelta.first_seen,
            ScanDelta.rows,
            ScanDelta.first_at,
            ScanDelta.history_rev == current,
        )
        .select_from(ScanDelta)
        .outerjoin(
            rev,
            and_(
                rev.scan_id == ScanDelta.scan_id, rev.dimension == ScanDelta.dimension
            ),
        )
        .where(ScanDelta.dimension == dimension, ScanDelta.scan_id.in_(scan_ids))
    )
    return query if loose else query.where(ScanDelta.history_rev == current)


def _stored_retired(dimension: str, pairs: list[Pair]):
    own = aliased(ScanRevision)
    prev = aliased(ScanRevision)
    return (
        select(ScanRetired.scan_id, ScanRetired.prev_scan_id, ScanRetired.retired)
        .select_from(ScanRetired)
        .outerjoin(
            own,
            and_(own.scan_id == ScanRetired.scan_id, own.dimension == dimension),
        )
        .outerjoin(
            prev,
            and_(prev.scan_id == ScanRetired.prev_scan_id, prev.dimension == dimension),
        )
        .where(
            ScanRetired.dimension == dimension,
            tuple_(ScanRetired.scan_id, ScanRetired.prev_scan_id).in_(pairs),
            ScanRetired.rows_rev == func.coalesce(own.rows_rev, 0),
            ScanRetired.prev_rows_rev == func.coalesce(prev.rows_rev, 0),
        )
    )


# ---------- read-through ----------


@dataclass(frozen=True)
class Facts:
    first_seen: int
    rows: int
    first_at: datetime | None


def _facts(
    session: Session, dimension: str, ids: list[UUID], reuse: frozenset[UUID]
) -> tuple[dict[UUID, Facts], Fill, set[UUID]]:
    if dimension not in FIRST_SEEN:
        msg = f"first-seen counts are not stored for {dimension}"
        raise ValueError(msg)
    out: dict[UUID, Facts] = {}
    stale: set[UUID] = set()
    if not ids:
        return out, Fill([], []), stale
    for scan_id, first, rows, first_at, fresh in session.execute(
        _stored_facts(dimension, ids, loose=bool(reuse))
    ).all():
        if fresh or scan_id in reuse:
            out[scan_id] = Facts(int(first), int(rows), first_at)
            if not fresh:
                stale.add(scan_id)
    fill: list[dict] = []
    for scan_id in ids:
        if scan_id in out:
            continue
        if scan_id in reuse:
            stale.add(scan_id)
            continue
        rev, first, rows, first_at = session.execute(
            _facts_statement(dimension, scan_id)
        ).one()
        out[scan_id] = Facts(int(first), int(rows), first_at)
        fill.append(
            {
                "scan_id": scan_id,
                "dimension": dimension,
                "history_rev": int(rev),
                "first_seen": int(first),
                "rows": int(rows),
                "first_at": first_at,
            }
        )
    return out, Fill(fill, []), stale


def first_seen(
    session: Session,
    dimension: str,
    scan_ids: Iterable[UUID],
    *,
    reuse: frozenset[UUID] = frozenset(),
) -> tuple[dict[UUID, int], Fill, set[UUID]]:
    """Per scan, the keys it was the first to report; a scan in `reuse` may answer stale."""
    facts, fill, stale = _facts(
        session, dimension, list(dict.fromkeys(scan_ids)), reuse
    )
    return {sid: f.first_seen for sid, f in facts.items()}, fill, stale


def row_counts(
    session: Session,
    dimension: str,
    scan_ids: Iterable[UUID],
    *,
    live: frozenset[UUID] = frozenset(),
) -> tuple[dict[UUID, tuple[int, datetime | None]], Fill]:
    """Per scan holding rows, how many and when the first landed; a live run is counted now."""
    ids = list(dict.fromkeys(scan_ids))
    settled = [sid for sid in ids if sid not in live]
    facts, fill, _ = _facts(session, dimension, settled, frozenset())
    out = {sid: (f.rows, f.first_at) for sid, f in facts.items() if f.rows}
    counting = [sid for sid in ids if sid in live]
    if counting:
        for scan_id, rows, first_at in session.execute(
            _rows_statement(dimension, counting)
        ).all():
            out[scan_id] = (int(rows), first_at)
    return out, fill


def retired(
    session: Session,
    dimension: str,
    pairs: Iterable[Pair],
) -> tuple[dict[Pair, int], Fill]:
    """Per (scan, previous scan), keys the previous one held that the scan lacks."""
    wanted = list(dict.fromkeys(pairs))
    if not wanted:
        return {}, Fill([], [])
    out: dict[Pair, int] = {
        (scan_id, prev_id): int(count)
        for scan_id, prev_id, count in session.execute(
            _stored_retired(dimension, wanted)
        ).all()
    }
    rows: list[dict] = []
    for pair in wanted:
        if pair in out:
            continue
        scan_id, prev_id = pair
        own, prev, count = session.execute(
            _retired_statement(dimension, scan_id, prev_id)
        ).one()
        out[pair] = int(count)
        rows.append(
            {
                "scan_id": scan_id,
                "prev_scan_id": prev_id,
                "dimension": dimension,
                "rows_rev": int(own),
                "prev_rows_rev": int(prev),
                "retired": int(count),
            }
        )
    return out, Fill([], rows)


def store(session: Session, fill: Fill) -> None:
    """Write computed counts; a count never replaces one taken at a later revision."""
    if fill.first_seen:
        stmt = insert(ScanDelta).values(
            sorted(fill.first_seen, key=lambda r: (str(r["scan_id"]), r["dimension"]))
        )
        session.execute(
            stmt.on_conflict_do_update(
                index_elements=[ScanDelta.scan_id, ScanDelta.dimension],
                set_={
                    "history_rev": stmt.excluded.history_rev,
                    "first_seen": stmt.excluded.first_seen,
                    "rows": stmt.excluded.rows,
                    "first_at": stmt.excluded.first_at,
                },
                where=ScanDelta.history_rev <= stmt.excluded.history_rev,
            )
        )
    if fill.retired:
        stmt = insert(ScanRetired).values(
            sorted(
                fill.retired,
                key=lambda r: (
                    str(r["scan_id"]),
                    str(r["prev_scan_id"]),
                    r["dimension"],
                ),
            )
        )
        session.execute(
            stmt.on_conflict_do_update(
                index_elements=[
                    ScanRetired.scan_id,
                    ScanRetired.prev_scan_id,
                    ScanRetired.dimension,
                ],
                set_={
                    "rows_rev": stmt.excluded.rows_rev,
                    "prev_rows_rev": stmt.excluded.prev_rows_rev,
                    "retired": stmt.excluded.retired,
                },
                where=and_(
                    ScanRetired.rows_rev <= stmt.excluded.rows_rev,
                    ScanRetired.prev_rows_rev <= stmt.excluded.prev_rows_rev,
                ),
            )
        )


# ---------- pairs ----------


def _ordering():
    return func.coalesce(Scan.started_at, Scan.created_at)


def previous_completed(target_ids: Iterable[UUID]):
    """Each completed census run of the targets beside the completed census run before it."""
    prev_id = (
        func.lag(Scan.id).over(partition_by=Scan.target_id, order_by=_ordering().asc())
    ).label("prev_id")
    return (
        select(Scan.id.label("id"), prev_id)
        .where(
            Scan.target_id.in_(list(target_ids)),
            Scan.status == ScanStatus.COMPLETED.value,
            census_only(),
        )
        .subquery()
    )


def warm_pairs(session: Session, scan: Scan) -> list[tuple[str, Pair]]:
    """The (dimension, pair) retired counts the views read for this run."""
    earlier = [
        census_only(),
        Scan.target_id == scan.target_id,
        Scan.id != scan.id,
        _ordering() < (scan.started_at or scan.created_at),
    ]
    out: list[tuple[str, Pair]] = []
    for dimension, model in TABLES.items():
        prev = session.execute(
            select(Scan.id)
            .where(*earlier, covers(model, dimension))
            .order_by(_ordering().desc())
            .limit(1)
        ).scalar_one_or_none()
        if prev is not None:
            out.append((dimension, (scan.id, prev)))
    completed = session.execute(
        select(Scan.id)
        .where(*earlier, Scan.status == ScanStatus.COMPLETED.value)
        .order_by(_ordering().desc())
        .limit(1)
    ).scalar_one_or_none()
    if completed is not None:
        out.append((WEB, (scan.id, completed)))
    return list(dict.fromkeys(out))


def warm(session: Session, scan: Scan) -> None:
    """Store every count the views read for a settled run."""
    for dimension in FIRST_SEEN:
        _, fill, _ = first_seen(session, dimension, [scan.id])
        store(session, fill)
    pairs: list[tuple[str, Pair]] = []
    if scan.status == ScanStatus.COMPLETED.value and scan.scope == ScanScope.FULL.value:
        pairs.extend(warm_pairs(session, scan))
    pairs.extend(
        (dimension, (newer, scan.id))
        for newer, dimension in session.execute(
            select(ScanRetired.scan_id, ScanRetired.dimension).where(
                ScanRetired.prev_scan_id == scan.id
            )
        ).all()
    )
    for dimension, pair in dict.fromkeys(pairs):
        _, fill = retired(session, dimension, [pair])
        store(session, fill)
    session.commit()


def refresh(session: Session, scan_id: UUID) -> None:
    """Recount a run whose stored first-seen counts moved."""
    for dimension in FIRST_SEEN:
        _, fill, _ = first_seen(session, dimension, [scan_id])
        store(session, fill)
    session.commit()


def pending_scans(session: Session, *, limit: int) -> list[UUID]:
    """Settled runs holding a first-seen count that is missing or out of date."""
    rev = aliased(ScanRevision)
    dims = select(
        func.unnest(literal(list(FIRST_SEEN), ARRAY(String))).label("d")
    ).subquery()
    valid = exists(
        select(1)
        .select_from(ScanDelta)
        .outerjoin(
            rev,
            and_(
                rev.scan_id == ScanDelta.scan_id, rev.dimension == ScanDelta.dimension
            ),
        )
        .where(
            ScanDelta.scan_id == Scan.id,
            ScanDelta.dimension == dims.c.d,
            ScanDelta.history_rev == func.coalesce(rev.history_rev, 0),
        )
        .correlate(Scan, dims)
    )
    missing = exists(select(1).select_from(dims).where(~valid).correlate(Scan))
    return list(
        session.execute(
            select(Scan.id)
            .where(Scan.status.in_(SCAN_TERMINAL_STATUSES), missing)
            .order_by(_ordering().desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
