"""Web assets over the census runs of a target: one cell per run, flags per host."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import lru_cache
from typing import TYPE_CHECKING, NamedTuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import (
    Boolean,
    Integer,
    Text,
    and_,
    case,
    cast,
    column,
    exists,
    func,
    not_,
    or_,
    select,
    text,
    values,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import aliased
from sqlalchemy.types import Uuid

from app.services.subdomain import SubdomainService
from shared.definitions.surface import SurfaceDimension
from shared.definitions.timeline import (
    ABSENT_STATES,
    FLAPPING_TRANSITIONS,
    WEB_ATTRIBUTE_LABELS,
    WEB_ATTRIBUTES,
    Observation,
    TimelineFlag,
    TimelineSort,
    WebAssetState,
)
from shared.enums.scan import SCAN_TERMINAL_STATUSES, ScanActivityStatus, ScanScope
from shared.logging import get_logger
from shared.models.asset_query import QueryError
from shared.models.scan import Scan
from shared.models.scan_activity import ScanActivity
from shared.models.subdomain import Subdomain
from shared.models.timeline import (
    TimelineCell,
    TimelineRow,
    TimelineScan,
    TimelineSearchResult,
)
from shared.services.asset_query import (
    NO_JIT,
    STATEMENT_TIMEOUT,
    TIMEOUT_SQLSTATE,
    QueryScope,
    QuerySyntaxError,
    query_error_for,
    syntax_error,
)
from shared.services.asset_query import predicates as preds
from shared.services.scan_scope import census_only, observing_stages
from shared.services.surface_query import web_assets as surface_hosts
from shared.utils.datetime import utc_now

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

WEB = SurfaceDimension.WEB_ASSETS.value
RAN = (ScanActivityStatus.SUCCESS.value, ScanActivityStatus.PARTIAL.value)
CLEAN = ScanActivityStatus.SUCCESS.value
GONE = WebAssetState.GONE.value
UNSEEN = WebAssetState.UNSEEN.value
ALL = "all"
SINCE = "since"
TIMED_OUT = QueryError(
    message="The Timeline timed out.", hint="Choose a smaller window."
)


class Sighting(NamedTuple):
    state: str
    status: int | None
    attributes: dict[str, object]


@dataclass(frozen=True)
class TimelineColumn:
    scan: Scan
    ord: int
    observation: str
    statuses: Mapping[str, str] = field(default_factory=dict)

    @property
    def observed(self) -> bool:
        return self.observation != Observation.UNOBSERVED.value

    @property
    def strict(self) -> bool:
        return self.observation == Observation.OBSERVED.value


@lru_cache(maxsize=1)
def _required_stages() -> frozenset[str]:
    """The observing stages a census run always carries."""
    from stages.registry import stages  # noqa: PLC0415

    return observing_stages()[WEB] & {s.name for s in stages() if s.always_on}


def observation_of(
    statuses: dict[str, str], required: frozenset[str] | None = None
) -> str:
    """What a run's observing stages say about its web asset rows."""
    required = _required_stages() if required is None else required
    if not statuses or not required <= set(statuses):
        return Observation.UNOBSERVED.value
    if any(state not in RAN for state in statuses.values()):
        return Observation.UNOBSERVED.value
    if all(state == CLEAN for state in statuses.values()):
        return Observation.OBSERVED.value
    return Observation.PARTIAL.value


def web_state():
    """The one SQL definition of a web asset's state."""
    return case(
        (preds.resolved().is_(False), WebAssetState.UNRESOLVED.value),
        (preds.status_class("2xx"), WebAssetState.LIVE.value),
        (preds.status_class("3xx"), WebAssetState.REDIRECT.value),
        (preds.status_class("4xx"), WebAssetState.CLIENT_ERROR.value),
        (preds.status_class("5xx"), WebAssetState.SERVER_ERROR.value),
        else_=WebAssetState.NO_HTTP.value,
    )


def _addresses():
    """The address set as jsonb, compared by containment both ways."""
    return func.coalesce(cast(Subdomain.resolved_ips, JSONB), func.jsonb_build_array())


def _attribute_hash():
    parts = []
    for name in WEB_ATTRIBUTES:
        if name == "resolved_ips":
            continue
        col = getattr(Subdomain, name)
        if name == "tls_expired":
            col = cast(col, Text)
        parts.append(func.coalesce(col, ""))
    return func.hashtextextended(func.concat_ws("|", *parts), 0)


def _attributes(row) -> dict[str, object]:
    out = {}
    for name in WEB_ATTRIBUTES:
        value = getattr(row, name)
        if name == "resolved_ips":
            value = set(value or [])
        out[name] = value
    return out


def _flag_column(flag: str) -> str:
    return f"flag_{flag}"


def _count_column(flag: str) -> str:
    return f"count_{flag}"


class TimelineService:
    result = TimelineSearchResult
    carried: tuple[str, ...] = ("transitions", "attribute_changes", "last_ord", "now")

    def __init__(self, session: AsyncSession):
        self.session = session

    def _stages(self) -> set[str]:
        return observing_stages()[WEB]

    def _since(self):
        """When the target first saw the host, across every scan."""
        other = aliased(Subdomain)
        return (
            select(func.min(other.discovered_at))
            .where(other.target_id == Subdomain.target_id, other.name == Subdomain.name)
            .correlate(Subdomain)
            .scalar_subquery()
        )

    def _required(self) -> frozenset[str]:
        return _required_stages()

    # ---------- window ----------

    async def _scan(self, scan_id: UUID, project_id: UUID) -> Scan:
        scan = await self.session.get(Scan, scan_id)
        if scan is None or scan.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found."
            )
        if scan.scope != ScanScope.FULL.value:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Timeline reads census runs. This run is focused.",
            )
        return scan

    @staticmethod
    def _runs_up_to(scan: Scan):
        started = func.coalesce(Scan.started_at, Scan.created_at)
        ran = exists(select(1).where(ScanActivity.scan_id == Scan.id))
        earlier = and_(
            Scan.id != scan.id,
            Scan.status.in_(SCAN_TERMINAL_STATUSES),
            started <= (scan.started_at or scan.created_at),
            ran,
        )
        return select(Scan).where(
            Scan.target_id == scan.target_id,
            Scan.project_id == scan.project_id,
            census_only(),
            or_(Scan.id == scan.id, earlier),
        )

    async def window(self, scan: Scan, window: int) -> list[Scan]:
        """The target's census runs up to the viewed one, oldest first."""
        started = func.coalesce(Scan.started_at, Scan.created_at)
        result = await self.session.execute(
            self._runs_up_to(scan)
            .order_by(started.desc(), Scan.created_at.desc())
            .limit(window)
        )
        return list(reversed(result.scalars().all()))

    async def runs(self, scan: Scan) -> int:
        """How many census runs the target has up to the viewed one."""
        return int(
            await self.session.scalar(
                select(func.count()).select_from(self._runs_up_to(scan).subquery())
            )
            or 0
        )

    async def _columns(self, scans: list[Scan]) -> list[TimelineColumn]:
        names = self._stages()
        result = await self.session.execute(
            select(ScanActivity.scan_id, ScanActivity.name, ScanActivity.status).where(
                ScanActivity.scan_id.in_([s.id for s in scans]),
                ScanActivity.name.in_(names),
                ScanActivity.status != ScanActivityStatus.SKIPPED.value,
            )
        )
        statuses: dict[UUID, dict[str, str]] = {s.id: {} for s in scans}
        for scan_id, name, state in result.all():
            statuses[scan_id][name] = state
        required = self._required()
        return [
            TimelineColumn(
                scan, i, observation_of(statuses[scan.id], required), statuses[scan.id]
            )
            for i, scan in enumerate(scans)
        ]

    # ---------- statements ----------

    @staticmethod
    def _values(columns: list[TimelineColumn]):
        rows = []
        observed_before = strict_before = 0
        for c in columns:
            later = [d.ord for d in columns if d.ord > c.ord and d.strict]
            rows.append(
                (
                    c.scan.id,
                    c.ord,
                    c.observed,
                    c.strict,
                    observed_before,
                    strict_before,
                    later[0] if later else None,
                )
            )
            observed_before += c.observed
            strict_before += c.strict
        return (
            values(
                column("scan_id", Uuid),
                column("ord", Integer),
                column("observed", Boolean),
                column("strict", Boolean),
                column("observed_before", Integer),
                column("strict_before", Integer),
                column("next_strict", Integer),
                name="timeline_scans",
            )
            .data(rows)
            .alias("w")
        )

    def _flags(self, w, project_id: UUID):
        """Per host: the changes in the window, the state now and the newest row."""
        rows = (
            select(
                Subdomain.id,
                Subdomain.name,
                w.c.ord,
                w.c.strict,
                w.c.observed_before,
                w.c.strict_before,
                cast(w.c.next_strict, Integer).label("next_strict"),
                web_state().label("st"),
                _attribute_hash().label("ah"),
                _addresses().label("ips"),
            )
            .join(w, w.c.scan_id == Subdomain.scan_id)
            .where(Subdomain.project_id == project_id, w.c.observed.is_(True))
            .cte("timeline_rows")
            .prefix_with("MATERIALIZED")
        )
        by_host = {"partition_by": rows.c.name, "order_by": rows.c.ord}

        def lag(col):
            return func.lag(col, type_=col.type).over(**by_host)

        seq = select(
            rows,
            lag(rows.c.ord).label("pord"),
            lag(rows.c.st).label("pst"),
            lag(rows.c.ah).label("pah"),
            lag(rows.c.ips).label("pips"),
            lag(rows.c.strict_before).label("pstrict_before"),
            lag(cast(rows.c.strict, Integer)).label("pstrict"),
            func.lead(rows.c.ord).over(**by_host).is_(None).label("last"),
        ).cte("timeline_seq")
        first = seq.c.pord.is_(None)
        gap = seq.c.strict_before - seq.c.pstrict_before - seq.c.pstrict > 0
        preceded = seq.c.observed_before > 0
        moved = case((first, 0), (gap, 2), (seq.c.st != seq.c.pst, 1), else_=0)
        same_addresses = and_(
            seq.c.ips.contains(seq.c.pips), seq.c.pips.contains(seq.c.ips)
        )
        attribute_moved = and_(
            not_(first),
            not_(gap),
            seq.c.st == seq.c.pst,
            or_(seq.c.ah != seq.c.pah, not_(same_addresses)),
        )
        noted = or_(moved > 0, attribute_moved, and_(first, preceded))
        appeared = or_(and_(first, preceded), and_(not_(first), gap))

        latest = func.array_agg(seq.c.id, type_=ARRAY(Uuid)).filter(seq.c.last)[1]
        tail = func.max(seq.c.next_strict).filter(seq.c.last)
        ended = tail.isnot(None)
        return (
            select(
                seq.c.name,
                latest.label("latest_id"),
                (func.sum(moved) + case((ended, 1), else_=0)).label("transitions"),
                func.count().filter(attribute_moved).label("attribute_changes"),
                func.greatest(func.max(seq.c.ord).filter(noted), tail).label(
                    "last_ord"
                ),
                func.min(seq.c.ord).label("first_ord"),
                func.bool_or(appeared).label("appeared"),
                case((ended, GONE), else_=func.max(seq.c.st).filter(seq.c.last)).label(
                    "now"
                ),
            )
            .group_by(seq.c.name)
            .cte("timeline_flags")
        )

    def _flag_predicates(self, flags, scan: Scan) -> dict[str, object]:
        changes = flags.c.transitions + flags.c.attribute_changes
        gone = flags.c.now == GONE
        is_new = preds.is_new(QueryScope((scan.id,), project_id=scan.project_id))
        return {
            TimelineFlag.NEW.value: is_new,
            TimelineFlag.GONE.value: gone,
            TimelineFlag.CHANGED.value: changes > 0,
            TimelineFlag.EPHEMERAL.value: and_(flags.c.appeared.is_(True), gone),
            TimelineFlag.FLAPPING.value: flags.c.transitions >= FLAPPING_TRANSITIONS,
            TimelineFlag.ATTRIBUTE.value: flags.c.attribute_changes > 0,
        }

    def _keyed_sorts(self, matched) -> dict[str, object]:
        return {
            TimelineSort.LAST_CHANGE.value: matched.c.last_ord,
            TimelineSort.CHANGES.value: matched.c.transitions
            + matched.c.attribute_changes,
            TimelineSort.FIRST_SEEN.value: matched.c[SINCE],
        }

    def _order(self, base, matched, host, f):
        desc = f.order == "desc"
        col = self._keyed_sorts(matched).get(f.sort)
        if col is None:
            return surface_hosts.order(base, f, host)
        primary = col.desc() if desc else col.asc()
        return base.order_by(primary.nulls_last(), host.name.asc(), host.id.asc())

    # ---------- read ----------

    async def search(self, project_id: UUID, scan_id: UUID, f):
        scan = await self._scan(scan_id, project_id)
        columns = await self._columns(await self.window(scan, f.window))
        runs = await self.runs(scan)
        scans = [
            TimelineScan(
                id=c.scan.id,
                started_at=c.scan.started_at or c.scan.created_at,
                status=c.scan.status,
                observation=c.observation,
            )
            for c in columns
        ]
        now = utc_now()
        scope = QueryScope(tuple(c.scan.id for c in columns), project_id=project_id)
        w = self._values(columns)
        flags = self._flags(w, project_id)
        by_flag = self._flag_predicates(flags, scan)
        try:
            predicate = surface_hosts.compiled(scope, f, now)
        except QuerySyntaxError as exc:
            return self.result(scans=scans, runs=runs, error=syntax_error(exc))
        keys = (*by_flag, ALL)
        base = surface_hosts.scoped(
            project_id,
            scope,
            f,
            now,
            columns=(
                Subdomain,
                *[flags.c[name] for name in self.carried],
                self._since().label(SINCE),
                *[pred.label(_flag_column(flag)) for flag, pred in by_flag.items()],
                *[
                    func.count().filter(pred).over().label(_count_column(flag))
                    for flag, pred in by_flag.items()
                ],
                func.count().over().label(_count_column(ALL)),
            ),
        ).join(flags, flags.c.latest_id == Subdomain.id)
        if predicate is not None:
            base = base.where(predicate)
        matched = base.cte("timeline_matched")
        host = aliased(Subdomain, matched)
        page = select(
            host,
            *[matched.c[name] for name in (*self.carried, SINCE)],
            *[matched.c[_flag_column(flag)] for flag in by_flag],
            *[matched.c[_count_column(key)] for key in keys],
        )
        if f.flag:
            page = page.where(matched.c[_flag_column(f.flag.value)])
        page = self._order(page, matched, host, f).limit(f.limit).offset(f.offset)

        await self.session.execute(text(STATEMENT_TIMEOUT))
        await self.session.execute(text(NO_JIT))
        try:
            rows = (await self.session.execute(page)).all()
            counts = await self._counts(rows, matched, keys, f)
            cells = await self._cells(w, columns, project_id, [r[0].name for r in rows])
        except DBAPIError as exc:
            await self.session.rollback()
            rejected = query_error_for(exc)
            if rejected is None:
                raise
            if getattr(exc.orig, "sqlstate", None) == TIMEOUT_SQLSTATE:
                rejected = TIMED_OUT
            logger.info("timeline query rejected by postgres", error=str(exc.orig))
            return self.result(scans=scans, runs=runs, error=rejected)

        reader = SubdomainService(self.session)
        items = [
            self._row(
                reader._to_read(row[0]),
                row._mapping,
                cells.get(row[0].name, []),
                columns,
                [flag for flag in by_flag if row._mapping[_flag_column(flag)]],
            )
            for row in rows
        ]
        return self.result(
            scans=scans,
            runs=runs,
            items=items,
            total=counts[f.flag.value if f.flag else ALL],
            counts=counts,
        )

    @staticmethod
    def _at(columns: list[TimelineColumn], ord_: int | None) -> UUID | None:
        return columns[ord_].scan.id if ord_ is not None else None

    def _row(self, host, m, cells, columns, flags: list[str]):
        return TimelineRow(
            host=host,
            cells=cells,
            state=m["now"],
            flags=flags,
            transitions=m["transitions"],
            attribute_changes=m["attribute_changes"],
            first_seen_at=m[SINCE],
            last_change_scan_id=self._at(columns, m["last_ord"]),
        )

    async def _counts(self, rows, matched, keys: tuple[str, ...], f) -> dict[str, int]:
        """The tab counts every page row carries."""
        row = rows[0]._mapping if rows else None
        if row is None and (f.flag or f.offset):
            row = (
                (
                    await self.session.execute(
                        select(*[matched.c[_count_column(key)] for key in keys]).limit(
                            1
                        )
                    )
                )
                .mappings()
                .first()
            )
        return {key: int(row[_count_column(key)]) if row else 0 for key in keys}

    async def _cells(
        self, w, columns: list[TimelineColumn], project_id: UUID, names: list[str]
    ) -> dict[str, list[TimelineCell]]:
        if not names:
            return {}
        result = await self.session.execute(
            select(
                Subdomain.name,
                w.c.ord,
                web_state().label("st"),
                Subdomain.http_status,
                *[getattr(Subdomain, name) for name in WEB_ATTRIBUTES],
            )
            .join(w, w.c.scan_id == Subdomain.scan_id)
            .where(
                Subdomain.project_id == project_id,
                Subdomain.name.in_(names),
                w.c.observed.is_(True),
            )
        )
        seen: dict[str, dict[int, Sighting]] = {}
        for row in result.all():
            seen.setdefault(row.name, {})[row.ord] = Sighting(
                row.st, row.http_status, _attributes(row)
            )
        return {name: self._strip(columns, seen.get(name, {})) for name in names}

    @staticmethod
    def _strip(
        columns: list[TimelineColumn], rows: dict[int, Sighting]
    ) -> list[TimelineCell]:
        first = min(rows) if rows else None
        cells: list[TimelineCell] = []
        previous: Sighting | None = None
        for col in columns:
            unseen = first is None or col.ord < first
            if not col.observed:
                state = UNSEEN if unseen else WebAssetState.UNOBSERVED.value
                cells.append(TimelineCell(state=state))
                continue
            row = rows.get(col.ord)
            if row is None:
                if unseen:
                    state = UNSEEN
                elif col.strict:
                    state = GONE
                else:
                    cells.append(TimelineCell(state=WebAssetState.UNCONFIRMED.value))
                    continue
                cells.append(TimelineCell(state=state))
                previous = Sighting(state, None, {})
                continue
            changed: list[str] = []
            if previous is not None and previous.state not in ABSENT_STATES:
                changed = [
                    WEB_ATTRIBUTE_LABELS[key]
                    for key in WEB_ATTRIBUTES
                    if previous.attributes.get(key) != row.attributes.get(key)
                ]
            cells.append(
                TimelineCell(state=row.state, status=row.status, changed=changed)
            )
            previous = row
        return cells


__all__ = [
    "TimelineColumn",
    "TimelineService",
    "observation_of",
    "web_state",
]
