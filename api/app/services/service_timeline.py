"""Ports over the census runs of a target: what opened and closed, by address and by port."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import NamedTuple
from uuid import UUID

from sqlalchemy import Integer, Text, and_, case, cast, func, not_, or_, select, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.exc import DBAPIError
from sqlalchemy.types import Uuid

from app.services.port import PortService
from app.services.timeline import (
    ALL,
    SINCE,
    TIMED_OUT,
    TimelineColumn,
    TimelineService,
    _count_column,
    _flag_column,
)
from shared.definitions.timeline import (
    FLAPPING_TRANSITIONS,
    MAX_CELL_ADDRESSES,
    SERVICE_STAGE,
    AddressFlag,
    AddressSort,
    AddressState,
    LaneState,
    PortFlag,
    PortSort,
    ServiceTimelineMode,
)
from shared.logging import get_logger
from shared.models.port import Port
from shared.models.scan import Scan
from shared.models.timeline import (
    AddressCell,
    LaneCell,
    PortCell,
    PortChange,
    ServiceAddressRow,
    ServiceLane,
    ServicePortRow,
    ServiceTimelineFilter,
    ServiceTimelineResult,
    TimelineScan,
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
from shared.services.surface_query import services as surface_services
from shared.utils.datetime import utc_now

logger = get_logger(__name__)

PORT_MODE = ServiceTimelineMode.PORT.value


class Sighting(NamedTuple):
    service_id: UUID
    service_name: str | None
    product: str | None
    version: str | None


class LaneKey(NamedTuple):
    ip: str
    port: int
    protocol: str


@dataclass
class LaneRecord:
    key: LaneKey
    row: object
    sightings: dict[int, Sighting] = field(default_factory=dict)


@dataclass
class Events:
    """What the lanes of one address did, per column."""

    opened: dict[int, list[PortChange]] = field(
        default_factory=lambda: defaultdict(list)
    )
    closed: dict[int, list[PortChange]] = field(
        default_factory=lambda: defaultdict(list)
    )
    software: dict[int, list[PortChange]] = field(
        default_factory=lambda: defaultdict(list)
    )
    present: set[int] = field(default_factory=set)


def _software(product, version) -> str:
    return f"{product or ''}|{version or ''}"


class ServiceTimelineService(TimelineService):
    result = ServiceTimelineResult

    def _stages(self) -> set[str]:
        return {SERVICE_STAGE}

    def _required(self) -> frozenset[str]:
        return frozenset({SERVICE_STAGE})

    # ---------- statements ----------

    def _rows(self, w, scope: QueryScope, f: ServiceTimelineFilter, now: datetime):
        """Every window row of the lanes that matched at any run, with their column."""
        d, matched = surface_services.scoped(
            scope, f, columns=lambda d: (d.c.ip, d.c.port, d.c.protocol)
        )
        predicate = surface_services.compiled(scope, f, now, d)
        if predicate is not None:
            matched = matched.where(predicate)
        keys = matched.distinct().cte("service_keys")
        return (
            select(
                d.c.id,
                d.c.scan_id,
                d.c.ip,
                d.c.inet,
                d.c.port,
                d.c.protocol,
                d.c.service_name,
                d.c.service_class,
                d.c.product,
                d.c.version_text,
                d.c.asn_org,
                d.c.country,
                d.c.is_cdn,
                d.c.host_count,
                w.c.ord,
                w.c.strict,
                w.c.strict_before,
                cast(w.c.next_strict, Integer).label("next_strict"),
                func.concat_ws(
                    "|",
                    func.coalesce(d.c.product, ""),
                    func.coalesce(d.c.version_text, ""),
                ).label("sw"),
            )
            .select_from(d)
            .join(
                keys,
                and_(
                    keys.c.ip == d.c.ip,
                    keys.c.port == d.c.port,
                    keys.c.protocol == d.c.protocol,
                ),
            )
            .join(w, w.c.scan_id == d.c.scan_id)
            .where(w.c.observed.is_(True))
            .cte("service_rows")
        )

    @staticmethod
    def _presence(w, project_id: UUID):
        """When each address first answered on any port in the window, before any filter."""
        return (
            select(Port.ip, func.min(w.c.ord).label("first_ord"))
            .join(w, w.c.scan_id == Port.scan_id)
            .where(Port.project_id == project_id, w.c.observed.is_(True))
            .group_by(Port.ip)
            .cte("service_presence")
        )

    @staticmethod
    def _lanes(rows, address_first):
        """Per address and port: the open and close events in the window, and the newest row."""
        by_lane = {
            "partition_by": (rows.c.ip, rows.c.port, rows.c.protocol),
            "order_by": rows.c.ord,
        }

        def lag(col):
            return func.lag(col, type_=col.type).over(**by_lane)

        seq = (
            select(
                rows,
                address_first.c.first_ord.label("address_first"),
                lag(rows.c.ord).label("pord"),
                lag(rows.c.strict_before).label("pstrict_before"),
                lag(cast(rows.c.strict, Integer)).label("pstrict"),
                lag(rows.c.next_strict).label("pnext"),
                lag(rows.c.sw).label("psw"),
                func.lead(rows.c.ord).over(**by_lane).is_(None).label("last"),
            )
            .join(address_first, address_first.c.ip == rows.c.ip)
            .cte("service_seq")
        )
        first = seq.c.pord.is_(None)
        gap = seq.c.strict_before - seq.c.pstrict_before - seq.c.pstrict > 0
        opened = case(
            (first, case((seq.c.ord > seq.c.address_first, 1), else_=0)),
            (gap, 1),
            else_=0,
        )
        closed_before = case((gap, 1), else_=0)
        ended = and_(seq.c.last, seq.c.next_strict.isnot(None))
        closed_after = case((ended, 1), else_=0)
        software_moved = and_(not_(first), seq.c.sw != seq.c.psw)
        eventful = or_(opened > 0, gap, software_moved)
        at_last = seq.c.last

        def newest(col, type_):
            return func.array_agg(col, type_=ARRAY(type_)).filter(at_last)[1]

        return (
            select(
                seq.c.ip,
                seq.c.port,
                seq.c.protocol,
                func.min(seq.c.ord).label("first_ord"),
                func.sum(opened).label("opened_events"),
                (func.sum(closed_before) + func.sum(closed_after)).label(
                    "closed_events"
                ),
                func.count().filter(software_moved).label("software_changes"),
                func.bool_or(and_(at_last, seq.c.next_strict.is_(None))).label(
                    "open_now"
                ),
                func.greatest(
                    func.max(seq.c.ord).filter(eventful),
                    func.max(seq.c.pnext).filter(gap),
                    func.max(seq.c.next_strict).filter(ended),
                ).label("last_ord"),
                newest(seq.c.id, Uuid).label("latest_id"),
                newest(seq.c.service_name, Text).label("service_name"),
                newest(seq.c.service_class, Text).label("service_class"),
                newest(seq.c.product, Text).label("product"),
                newest(seq.c.version_text, Text).label("version"),
                func.max(seq.c.inet).label("inet"),
                func.max(seq.c.asn_org).label("asn_org"),
                func.max(seq.c.country).label("country"),
                func.bool_or(seq.c.is_cdn).label("is_cdn"),
                func.max(seq.c.host_count).label("host_count"),
            )
            .group_by(seq.c.ip, seq.c.port, seq.c.protocol)
            .cte("service_lanes")
        )

    def _address_since(self, scan: Scan):
        return (
            select(Port.ip, func.min(Port.discovered_at).label(SINCE))
            .where(Port.target_id == scan.target_id)
            .group_by(Port.ip)
            .cte("service_address_since")
        )

    def _port_since(self, scan: Scan):
        return (
            select(
                Port.number, Port.protocol, func.min(Port.discovered_at).label(SINCE)
            )
            .where(Port.target_id == scan.target_id)
            .group_by(Port.number, Port.protocol)
            .cte("service_port_since")
        )

    # ---------- read ----------

    async def search(
        self, project_id: UUID, scan_id: UUID, f: ServiceTimelineFilter
    ) -> ServiceTimelineResult:
        scan = await self._scan(scan_id, project_id)
        columns = await self._columns(await self.window(scan, f.window))
        scans = [
            TimelineScan(
                id=c.scan.id,
                started_at=c.scan.started_at or c.scan.created_at,
                status=c.scan.status,
                observation=c.observation,
            )
            for c in columns
        ]
        mode = f.mode
        scope = QueryScope(tuple(c.scan.id for c in columns), project_id=project_id)
        w = self._values(columns)
        try:
            rows = self._rows(w, scope, f, utc_now())
        except QuerySyntaxError as exc:
            return ServiceTimelineResult(
                scans=scans, mode=mode, error=syntax_error(exc)
            )

        await self.session.execute(text(STATEMENT_TIMEOUT))
        await self.session.execute(text(NO_JIT))
        try:
            if mode == ServiceTimelineMode.PORT:
                return await self._by_port(scan, scans, columns, w, rows, f)
            return await self._by_address(scan, scans, columns, scope, w, rows, f)
        except DBAPIError as exc:
            await self.session.rollback()
            rejected = query_error_for(exc)
            if rejected is None:
                raise
            if getattr(exc.orig, "sqlstate", None) == TIMEOUT_SQLSTATE:
                rejected = TIMED_OUT
            logger.info("service timeline rejected by postgres", error=str(exc.orig))
            return ServiceTimelineResult(scans=scans, mode=mode, error=rejected)

    @staticmethod
    def _started(scan: Scan) -> datetime:
        return scan.started_at or scan.created_at

    async def _page(self, matched, keys, order, f):
        """The ordered page of a matched CTE and the counts every row carries."""
        page = select(matched)
        if f.flag:
            page = page.where(matched.c[_flag_column(f.flag.value)])
        rows = (
            await self.session.execute(order(page).limit(f.limit).offset(f.offset))
        ).all()
        counts = await self._counts(rows, matched, keys, f)
        return [row._mapping for row in rows], counts

    @staticmethod
    def _ordered(page, keyed: dict, tiebreak, f):
        col = keyed[f.sort] if f.sort in keyed else next(iter(keyed.values()))
        primary = col.desc() if f.order == "desc" else col.asc()
        return page.order_by(primary.nulls_last(), *tiebreak)

    # ---------- by address ----------

    async def _by_address(self, scan, scans, columns, scope, w, rows, f):
        presence = self._presence(w, scan.project_id)
        lanes = self._lanes(rows, presence)
        since = self._address_since(scan)
        agg = (
            select(
                lanes.c.ip,
                func.max(lanes.c.inet).label("inet"),
                func.sum(lanes.c.opened_events).label("opened"),
                func.sum(lanes.c.closed_events).label("closed"),
                func.sum(lanes.c.software_changes).label("software"),
                func.count().filter(lanes.c.open_now).label("open_now"),
                func.max(lanes.c.last_ord).label("last_ord"),
                func.min(presence.c.first_ord).label("first_ord"),
                func.max(lanes.c.opened_events + lanes.c.closed_events).label("events"),
                func.max(lanes.c.asn_org).label("asn_org"),
                func.max(lanes.c.country).label("country"),
                func.bool_or(lanes.c.is_cdn).label("is_cdn"),
                func.max(lanes.c.host_count).label("host_count"),
            )
            .select_from(lanes)
            .join(presence, presence.c.ip == lanes.c.ip)
            .group_by(lanes.c.ip)
            .cte("service_addresses")
        )
        first_seen = since.c[SINCE]
        by_flag = {
            AddressFlag.OPENED.value: agg.c.opened > 0,
            AddressFlag.CLOSED.value: agg.c.closed > 0,
            AddressFlag.NEW.value: first_seen >= self._started(scan),
            AddressFlag.GONE.value: agg.c.open_now == 0,
            AddressFlag.SOFTWARE.value: agg.c.software > 0,
            AddressFlag.FLAPPING.value: agg.c.events >= FLAPPING_TRANSITIONS,
        }
        keys = (*by_flag, ALL)
        matched = (
            select(
                agg,
                first_seen.label(SINCE),
                *[pred.label(_flag_column(flag)) for flag, pred in by_flag.items()],
                *[
                    func.count().filter(pred).over().label(_count_column(flag))
                    for flag, pred in by_flag.items()
                ],
                func.count().over().label(_count_column(ALL)),
            )
            .select_from(agg)
            .outerjoin(since, since.c.ip == agg.c.ip)
            .cte("service_matched")
        )
        keyed = {
            AddressSort.LAST_CHANGE.value: matched.c.last_ord,
            AddressSort.CHANGES.value: matched.c.opened
            + matched.c.closed
            + matched.c.software,
            AddressSort.FIRST_SEEN.value: matched.c[SINCE],
            AddressSort.OPEN.value: matched.c.open_now,
            AddressSort.ADDRESS.value: matched.c.inet,
        }
        page, counts = await self._page(
            matched,
            keys,
            lambda q: self._ordered(
                q, keyed, (matched.c.inet.asc(), matched.c.ip.asc()), f
            ),
            f,
        )
        ips = [r["ip"] for r in page]
        records = await self._lane_records(rows, lanes, ips)
        hosts = await PortService(self.session).hosts_for(scope, ips) if ips else {}
        lane_since = await self._lane_since(scan, ips)
        port_since = await self._port_first(
            scan, {k.port for k in records} if records else set()
        )
        items = []
        for r in page:
            own = [rec for key, rec in records.items() if key.ip == r["ip"]]
            own.sort(key=lambda rec: (rec.key.port, rec.key.protocol))
            cells, lane_rows = self._address_strip(
                columns, own, r["first_ord"], lane_since, port_since
            )
            names = sorted(hosts.get(r["ip"], set()))
            items.append(
                ServiceAddressRow(
                    ip=r["ip"],
                    hosts=names[:5],
                    host_count=max(len(names), int(r["host_count"] or 0)),
                    asn_org=r["asn_org"],
                    country=r["country"],
                    is_cdn=bool(r["is_cdn"]),
                    cells=cells,
                    lanes=lane_rows,
                    flags=[flag for flag in by_flag if r[_flag_column(flag)]],
                    open_now=int(r["open_now"]),
                    changes=int(r["opened"] + r["closed"] + r["software"]),
                    first_seen_at=r[SINCE],
                    last_change_scan_id=self._at(columns, r["last_ord"]),
                )
            )
        return ServiceTimelineResult(
            scans=scans,
            mode=f.mode,
            addresses=items,
            total=counts[f.flag.value if f.flag else ALL],
            counts=counts,
        )

    async def _lane_records(
        self, rows, lanes, ips: list[str]
    ) -> dict[LaneKey, LaneRecord]:
        if not ips:
            return {}
        records: dict[LaneKey, LaneRecord] = {}
        for lane in (
            await self.session.execute(select(lanes).where(lanes.c.ip.in_(ips)))
        ).mappings():
            key = LaneKey(lane["ip"], int(lane["port"]), lane["protocol"])
            records[key] = LaneRecord(key, lane)
        seen = await self.session.execute(
            select(
                rows.c.ip,
                rows.c.port,
                rows.c.protocol,
                rows.c.ord,
                rows.c.id,
                rows.c.service_name,
                rows.c.product,
                rows.c.version_text,
            ).where(rows.c.ip.in_(ips))
        )
        for ip, port, protocol, ord_, sid, name, product, version in seen.all():
            record = records.get(LaneKey(ip, int(port), protocol))
            if record is not None:
                record.sightings[ord_] = Sighting(sid, name, product, version)
        return records

    async def _lane_since(
        self, scan: Scan, ips: list[str]
    ) -> dict[tuple[str, int, str], datetime]:
        if not ips:
            return {}
        result = await self.session.execute(
            select(Port.ip, Port.number, Port.protocol, func.min(Port.discovered_at))
            .where(Port.target_id == scan.target_id, Port.ip.in_(ips))
            .group_by(Port.ip, Port.number, Port.protocol)
        )
        return {
            (ip, int(number), protocol): at for ip, number, protocol, at in result.all()
        }

    async def _port_first(
        self, scan: Scan, ports: set[int]
    ) -> dict[tuple[int, str], datetime]:
        if not ports:
            return {}
        result = await self.session.execute(
            select(Port.number, Port.protocol, func.min(Port.discovered_at))
            .where(Port.target_id == scan.target_id, Port.number.in_(ports))
            .group_by(Port.number, Port.protocol)
        )
        return {(int(number), protocol): at for number, protocol, at in result.all()}

    def _address_strip(
        self,
        columns: list[TimelineColumn],
        lanes: list[LaneRecord],
        address_first: int,
        lane_since: dict,
        port_since: dict,
    ) -> tuple[list[AddressCell], list[ServiceLane]]:
        """The address's cells and its lanes, one state machine per lane over the columns."""
        events = Events()
        lane_rows = [
            self._lane_strip(
                columns,
                lane,
                address_first,
                lane_since.get(lane.key),
                port_since.get((lane.key.port, lane.key.protocol)),
                events,
            )
            for lane in lanes
        ]
        return self._address_cells(columns, address_first, events), lane_rows

    def _lane_strip(
        self,
        columns: list[TimelineColumn],
        lane: LaneRecord,
        address_first: int,
        since: datetime | None,
        first_on_target: datetime | None,
        events: Events,
    ) -> ServiceLane:
        key = lane.key
        first = min(lane.sightings) if lane.sightings else None
        cells: list[LaneCell] = []
        is_open = False
        streak_start: datetime | None = None
        previous: Sighting | None = None
        opened_at = closed_at = None
        for col in columns:
            unseen = first is None or col.ord < first
            if not col.observed:
                state = LaneState.UNSEEN.value if unseen else LaneState.UNOBSERVED.value
                cells.append(LaneCell(state=state))
                continue
            sighting = lane.sightings.get(col.ord)
            if sighting is not None:
                events.present.add(col.ord)
                started = self._started(col.scan)
                change = PortChange(
                    port=key.port,
                    protocol=key.protocol,
                    service_name=sighting.service_name,
                    product=sighting.product,
                    version=sighting.version,
                    first_on_address=since is not None and since >= started,
                    first_on_target=first_on_target is not None
                    and first_on_target >= started,
                )
                if not is_open:
                    is_open = True
                    streak_start = started
                    if col.ord > address_first:
                        events.opened[col.ord].append(change)
                        opened_at = col.ord
                moved = previous is not None and _software(
                    previous.product, previous.version
                ) != _software(sighting.product, sighting.version)
                if moved:
                    events.software[col.ord].append(change)
                cells.append(
                    LaneCell(
                        state=LaneState.OPEN.value,
                        service_id=sighting.service_id,
                        software_changed=moved,
                    )
                )
                previous = sighting
                continue
            if unseen:
                cells.append(LaneCell(state=LaneState.UNSEEN.value))
            elif col.strict:
                if is_open and previous is not None:
                    is_open = False
                    events.closed[col.ord].append(
                        PortChange(
                            port=key.port,
                            protocol=key.protocol,
                            service_name=previous.service_name,
                            product=previous.product,
                            version=previous.version,
                            open_since=since
                            if since and streak_start and since < streak_start
                            else streak_start,
                        )
                    )
                    closed_at = col.ord
                cells.append(LaneCell(state=LaneState.CLOSED.value))
            else:
                state = (
                    LaneState.UNCONFIRMED.value if is_open else LaneState.CLOSED.value
                )
                cells.append(LaneCell(state=state))
        row = lane.row
        return ServiceLane(
            port=key.port,
            protocol=key.protocol,
            service_name=row["service_name"],
            service_class=row["service_class"],
            product=row["product"],
            version=row["version"],
            open_now=bool(row["open_now"]),
            cells=cells,
            first_seen_at=since,
            opened_scan_id=self._at(columns, opened_at),
            closed_scan_id=self._at(columns, closed_at),
            events=int(row["opened_events"] + row["closed_events"]),
            software_changes=int(row["software_changes"]),
        )

    @staticmethod
    def _address_cells(
        columns: list[TimelineColumn], address_first: int, events: Events
    ) -> list[AddressCell]:
        cells: list[AddressCell] = []
        was_open = False
        first_present = min(events.present, default=None)
        for col in columns:
            unseen = first_present is None or col.ord < first_present
            if not col.observed:
                state = (
                    AddressState.UNSEEN.value
                    if unseen
                    else AddressState.UNOBSERVED.value
                )
                cells.append(AddressCell(state=state))
                continue
            up = events.opened.get(col.ord, [])
            down = events.closed.get(col.ord, [])
            moved = events.software.get(col.ord, [])
            present = col.ord in events.present
            if col.ord == first_present and col.ord == address_first:
                state = AddressState.FIRST.value
            elif up and down:
                state = AddressState.BOTH.value
            elif up:
                state = AddressState.OPENED.value
            elif down:
                state = AddressState.CLOSED.value
            elif present:
                state = AddressState.SAME.value
            elif unseen:
                state = AddressState.UNSEEN.value
            elif col.strict or not was_open:
                state = AddressState.GONE.value
            else:
                state = AddressState.UNCONFIRMED.value
            was_open = present or (was_open and not col.strict)
            cells.append(
                AddressCell(state=state, opened=up, closed=down, software=moved)
            )
        return cells

    # ---------- by port ----------

    async def _by_port(self, scan, scans, columns, w, rows, f):
        counted = (
            select(
                rows.c.port,
                rows.c.protocol,
                rows.c.ord,
                func.count(func.distinct(rows.c.ip)).label("n"),
            )
            .group_by(rows.c.port, rows.c.protocol, rows.c.ord)
            .cte("service_port_counts")
        )
        ports = select(rows.c.port, rows.c.protocol).distinct().cte("service_ports")
        grid = (
            select(
                ports.c.port,
                ports.c.protocol,
                w.c.ord,
                func.coalesce(counted.c.n, 0).label("n"),
            )
            .select_from(ports)
            .join(w, w.c.strict.is_(True))
            .outerjoin(
                counted,
                and_(
                    counted.c.port == ports.c.port,
                    counted.c.protocol == ports.c.protocol,
                    counted.c.ord == w.c.ord,
                ),
            )
            .cte("service_port_grid")
        )
        by_port = {
            "partition_by": (grid.c.port, grid.c.protocol),
            "order_by": grid.c.ord,
        }
        seq = select(grid, func.lag(grid.c.n).over(**by_port).label("pn")).cte(
            "service_port_seq"
        )
        delta = seq.c.n - seq.c.pn
        moved = and_(seq.c.pn.isnot(None), delta != 0)
        newest_ord = max((c.ord for c in columns if c.observed), default=-1)
        latest = (
            select(
                rows.c.port,
                rows.c.protocol,
                func.array_agg(rows.c.service_name, type_=ARRAY(Text))
                .filter(rows.c.ord == newest_ord)[1]
                .label("service_name"),
                func.array_agg(rows.c.product, type_=ARRAY(Text))
                .filter(rows.c.ord == newest_ord)[1]
                .label("product"),
                func.max(rows.c.service_name).label("any_service"),
                func.max(rows.c.product).label("any_product"),
                func.count(func.distinct(rows.c.ip))
                .filter(rows.c.ord == newest_ord)
                .label("now"),
            )
            .group_by(rows.c.port, rows.c.protocol)
            .cte("service_port_latest")
        )
        since = self._port_since(scan)
        agg = (
            select(
                seq.c.port,
                seq.c.protocol,
                func.max(seq.c.n).label("peak"),
                func.bool_or(and_(moved, delta > 0)).label("spread"),
                func.bool_or(and_(moved, delta < 0)).label("shrank"),
                func.max(seq.c.ord).filter(moved).label("last_ord"),
            )
            .group_by(seq.c.port, seq.c.protocol)
            .cte("service_port_agg")
        )
        first_seen = since.c[SINCE]
        by_flag = {
            PortFlag.SPREAD.value: func.coalesce(agg.c.spread, False),
            PortFlag.SHRANK.value: func.coalesce(agg.c.shrank, False),
            PortFlag.NEW.value: first_seen >= self._started(scan),
            PortFlag.GONE.value: and_(
                latest.c.now == 0, func.coalesce(agg.c.peak, 0) > 0
            ),
        }
        keys = (*by_flag, ALL)
        matched = (
            select(
                latest.c.port,
                latest.c.protocol,
                func.coalesce(latest.c.service_name, latest.c.any_service).label(
                    "service_name"
                ),
                func.coalesce(latest.c.product, latest.c.any_product).label("product"),
                latest.c.now,
                func.coalesce(agg.c.peak, 0).label("peak"),
                agg.c.last_ord,
                first_seen.label(SINCE),
                *[pred.label(_flag_column(flag)) for flag, pred in by_flag.items()],
                *[
                    func.count().filter(pred).over().label(_count_column(flag))
                    for flag, pred in by_flag.items()
                ],
                func.count().over().label(_count_column(ALL)),
            )
            .select_from(latest)
            .outerjoin(
                agg,
                and_(agg.c.port == latest.c.port, agg.c.protocol == latest.c.protocol),
            )
            .outerjoin(
                since,
                and_(
                    since.c.number == latest.c.port,
                    since.c.protocol == latest.c.protocol,
                ),
            )
            .cte("service_matched")
        )
        keyed = {
            PortSort.ADDRESSES.value: matched.c.now,
            PortSort.LAST_CHANGE.value: matched.c.last_ord,
            PortSort.FIRST_SEEN.value: matched.c[SINCE],
            PortSort.PORT.value: matched.c.port,
        }
        page, counts = await self._page(
            matched,
            keys,
            lambda q: self._ordered(
                q, keyed, (matched.c.port.asc(), matched.c.protocol.asc()), f
            ),
            f,
        )
        members = await self._port_members(
            rows, [(int(r["port"]), r["protocol"]) for r in page]
        )
        items = [
            ServicePortRow(
                port=int(r["port"]),
                protocol=r["protocol"],
                service_name=r["service_name"],
                product=r["product"],
                cells=self._port_strip(
                    columns, members.get((int(r["port"]), r["protocol"]), {})
                ),
                flags=[flag for flag in by_flag if r[_flag_column(flag)]],
                now=int(r["now"]),
                peak=int(r["peak"]),
                first_seen_at=r[SINCE],
                last_change_scan_id=self._at(columns, r["last_ord"]),
            )
            for r in page
        ]
        return ServiceTimelineResult(
            scans=scans,
            mode=f.mode,
            ports=items,
            total=counts[f.flag.value if f.flag else ALL],
            counts=counts,
        )

    async def _port_members(
        self, rows, ports: list[tuple[int, str]]
    ) -> dict[tuple[int, str], dict[int, set[str]]]:
        if not ports:
            return {}
        result = await self.session.execute(
            select(rows.c.port, rows.c.protocol, rows.c.ord, rows.c.ip).where(
                rows.c.port.in_(sorted({p for p, _ in ports}))
            )
        )
        members: dict[tuple[int, str], dict[int, set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )
        for port, protocol, ord_, ip in result.all():
            members[(int(port), protocol)][ord_].add(ip)
        return members

    @staticmethod
    def _port_strip(
        columns: list[TimelineColumn], members: dict[int, set[str]]
    ) -> list[PortCell]:
        cells: list[PortCell] = []
        previous: set[str] | None = None
        for col in columns:
            if not col.observed:
                cells.append(PortCell(state=AddressState.UNOBSERVED.value))
                continue
            now = members.get(col.ord, set())
            if not col.strict:
                cells.append(
                    PortCell(state=AddressState.UNCONFIRMED.value, count=len(now))
                )
                continue
            added = sorted(now - previous) if previous is not None else []
            removed = sorted(previous - now) if previous is not None else []
            cells.append(
                PortCell(
                    state=AddressState.SAME.value,
                    count=len(now),
                    delta=len(now) - len(previous) if previous is not None else 0,
                    added=added[:MAX_CELL_ADDRESSES],
                    removed=removed[:MAX_CELL_ADDRESSES],
                    more=max(0, len(added) - MAX_CELL_ADDRESSES)
                    + max(0, len(removed) - MAX_CELL_ADDRESSES),
                )
            )
            previous = now
        return cells


__all__ = ["ServiceTimelineService"]
