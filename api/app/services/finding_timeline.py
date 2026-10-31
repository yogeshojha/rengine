"""Findings over the census runs of a target: when each was found, fixed and came back."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from statistics import median
from typing import TYPE_CHECKING, NamedTuple
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from app.services.timeline import ALL, TIMED_OUT, TimelineColumn, TimelineService
from app.services.vulnerability import VulnerabilityService
from shared.definitions.scan_surface import SurfaceClass
from shared.definitions.surface import SurfaceDimension
from shared.definitions.timeline import (
    FINDING_GROUP_ORDER,
    MAX_CELL_HOSTS,
    MAX_TIMELINE_FINDINGS,
    PRESENT_STATES,
    CheckFlag,
    CheckSort,
    CheckState,
    FindingGroup,
    FindingSort,
    FindingState,
    FindingTimelineMode,
)
from shared.definitions.vulnerabilities import (
    SUPPRESSED_STATES,
    Scanner,
    VulnState,
    severity_rank,
)
from shared.logging import get_logger
from shared.models.asset_query import QueryError
from shared.models.scan import Scan
from shared.models.scan_surface import ScanSurfaceItem
from shared.models.timeline import (
    CheckCell,
    CheckRow,
    CheckStats,
    FindingCell,
    FindingLifespan,
    FindingStats,
    FindingTimelineFilter,
    FindingTimelineResult,
    LifeSegment,
    RunPoint,
    TimelineScan,
)
from shared.models.vuln_template import VulnTemplate
from shared.models.vulnerability import (
    Vulnerability,
    VulnerabilityCoverage,
    VulnerabilityTriage,
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
from shared.services.issue_tracking.sync import (
    DAST_STAGE,
    DAST_TAG,
    SCANNED_STATES,
    VULN_STAGE,
)
from shared.services.scan_scope import observing_stages
from shared.services.scan_surface import wants_callback
from shared.services.surface_query import vulnerabilities as surface_vulns
from shared.services.vuln_templates import (
    dast_predicate,
    picked_predicate,
    selection_predicate,
)
from shared.utils.datetime import utc_now

if TYPE_CHECKING:
    from collections.abc import Iterable

logger = get_logger(__name__)

VULNS = SurfaceDimension.VULNERABILITIES.value
OPEN = FindingState.OPEN.value
REGRESSED = FindingState.REGRESSED.value
FIXED = FindingState.FIXED.value
NOT_TESTED = FindingState.NOT_TESTED.value
UNOBSERVED = FindingState.UNOBSERVED.value
UNSEEN = FindingState.UNSEEN.value
TOO_MANY = QueryError(
    message="Too many findings for the Timeline.", hint="Narrow the query."
)


class Sighting(NamedTuple):
    id: UUID
    severity: str
    host: str | None
    ip: str | None
    port: int | None
    template_id: str
    template_name: str
    scanner: str
    tags: list
    is_kev: bool
    discovered_at: datetime
    replayed_from_id: UUID | None


class Locator(NamedTuple):
    host: str
    port: int | None


@dataclass
class Life:
    """One finding's walk over the columns."""

    fingerprint: str
    newest: Sighting
    cells: list[str]
    segments: list[LifeSegment]
    group: str
    state: str
    open_since: datetime | None = None
    open_days: int | None = None
    fixed_at: datetime | None = None
    fixed_ord: int | None = None
    regressions: int = 0
    returned_ord: int | None = None
    not_tested_runs: int = 0
    tested_runs: int = 0
    is_new: bool = False
    triage_state: str = VulnState.OPEN.value
    first_seen_at: datetime | None = None
    last_change_ord: int | None = None


@dataclass
class Tested:
    """What each run selected and scanned, read once per window."""

    selected: dict[int, set[str]] = field(default_factory=dict)
    scanned: dict[UUID, set[Locator]] = field(default_factory=dict)

    def covers(self, col: TimelineColumn, row: Sighting) -> bool:
        if not col.strict or row.scanner != Scanner.NUCLEI.value or not row.host:
            return False
        if row.template_id not in self.selected.get(col.ord, ()):
            return False
        return Locator(row.host.lower(), row.port or None) in self.scanned.get(
            col.scan.id, ()
        )


def _days(start: datetime, end: datetime) -> int:
    return max(0, (end - start).days)


def _started(col: TimelineColumn) -> datetime:
    return col.scan.started_at or col.scan.created_at


def _stage_config(model, configs: dict, name: str, statuses) -> object | None:
    if name not in statuses:
        return None
    try:
        return model.model_validate(configs.get(name) or {})
    except ValidationError:
        return None


class FindingTimelineService(TimelineService):
    result = FindingTimelineResult

    def _stages(self) -> set[str]:
        return observing_stages()[VULNS]

    def _required(self) -> frozenset[str]:
        return frozenset()

    # ---------- read ----------

    async def search(
        self, project_id: UUID, scan_id: UUID, f: FindingTimelineFilter
    ) -> FindingTimelineResult:
        scan = await self._scan(scan_id, project_id)
        columns = await self._columns(await self.window(scan, f.window))
        runs = await self.runs(scan)
        scans = [
            TimelineScan(
                id=c.scan.id,
                started_at=_started(c),
                status=c.scan.status,
                observation=c.observation,
            )
            for c in columns
        ]
        mode = f.mode
        f = _flag_for_mode(f)
        scope = QueryScope(tuple(c.scan.id for c in columns), project_id=project_id)
        w = self._values(columns)
        try:
            keys = self._keys(scope, f)
        except QuerySyntaxError as exc:
            return FindingTimelineResult(
                scans=scans, runs=runs, mode=mode, error=syntax_error(exc)
            )

        await self.session.execute(text(STATEMENT_TIMEOUT))
        await self.session.execute(text(NO_JIT))
        try:
            if await self._too_many(keys):
                return FindingTimelineResult(
                    scans=scans, runs=runs, mode=mode, error=TOO_MANY
                )
            history = await self._history(w, keys, project_id)
            fingerprints = list(history)
            newest = {fp: rows[max(rows)] for fp, rows in history.items()}
            triage = await self._triage(scan, fingerprints, newest)
            tested = await self._tested(columns, newest.values())
            if mode == FindingTimelineMode.CHECKS:
                result = await self._by_check(
                    scan, columns, history, newest, triage, tested, f
                )
            else:
                result = await self._lifespans(
                    scan, scope, columns, history, newest, triage, tested, f
                )
        except DBAPIError as exc:
            await self.session.rollback()
            rejected = query_error_for(exc)
            if rejected is None:
                raise
            if getattr(exc.orig, "sqlstate", None) == TIMEOUT_SQLSTATE:
                rejected = TIMED_OUT
            logger.info("finding timeline rejected by postgres", error=str(exc.orig))
            return FindingTimelineResult(
                scans=scans, runs=runs, mode=mode, error=rejected
            )
        result.scans = scans
        result.runs = runs
        result.mode = mode
        return result

    # ---------- statements ----------

    @staticmethod
    def _keys(scope: QueryScope, f: FindingTimelineFilter):
        """The fingerprints the filter matches at any run of the window."""
        wide = f.model_copy(update={"include_suppressed": True})
        predicate = surface_vulns.compiled(scope, wide, utc_now())
        base = surface_vulns.scoped(scope, wide, columns=(Vulnerability.fingerprint,))
        if predicate is not None:
            base = base.where(predicate)
        return base.distinct().cte("finding_keys")

    async def _too_many(self, keys) -> bool:
        counted = await self.session.scalar(
            select(func.count()).select_from(
                select(keys.c.fingerprint).limit(MAX_TIMELINE_FINDINGS + 1).subquery()
            )
        )
        return int(counted or 0) > MAX_TIMELINE_FINDINGS

    async def _history(
        self, w, keys, project_id: UUID
    ) -> dict[str, dict[int, Sighting]]:
        result = await self.session.execute(
            select(
                Vulnerability.fingerprint,
                w.c.ord,
                Vulnerability.id,
                Vulnerability.severity,
                Vulnerability.host,
                Vulnerability.ip,
                Vulnerability.port,
                Vulnerability.template_id,
                Vulnerability.template_name,
                Vulnerability.scanner,
                Vulnerability.tags,
                Vulnerability.is_kev,
                Vulnerability.discovered_at,
                Vulnerability.replayed_from_id,
            )
            .join(w, w.c.scan_id == Vulnerability.scan_id)
            .where(
                Vulnerability.project_id == project_id,
                Vulnerability.fingerprint.in_(select(keys.c.fingerprint)),
            )
        )
        history: dict[str, dict[int, Sighting]] = defaultdict(dict)
        for row in result.all():
            history[row.fingerprint][row.ord] = Sighting(*row[2:])
        return history

    async def _triage(
        self, scan: Scan, fingerprints: list[str], newest: dict[str, Sighting]
    ) -> dict[str, str]:
        """Each finding's review state, a replay reading its source's."""
        sources = {
            row.replayed_from_id
            for row in newest.values()
            if row.replayed_from_id is not None
        }
        source_of: dict[UUID, str] = {}
        if sources:
            rows = await self.session.execute(
                select(Vulnerability.id, Vulnerability.fingerprint).where(
                    Vulnerability.id.in_(sources)
                )
            )
            source_of = dict(rows.all())
        wanted = set(fingerprints) | set(source_of.values())
        rows = await self.session.execute(
            select(VulnerabilityTriage.fingerprint, VulnerabilityTriage.state).where(
                VulnerabilityTriage.target_id == scan.target_id,
                VulnerabilityTriage.fingerprint.in_(wanted),
            )
        )
        states = dict(rows.all())
        out: dict[str, str] = {}
        for fp, row in newest.items():
            own = states.get(fp)
            source = states.get(source_of.get(row.replayed_from_id, ""))
            if own in SUPPRESSED_STATES or source not in SUPPRESSED_STATES:
                out[fp] = own or VulnState.OPEN.value
            else:
                out[fp] = source
        return out

    async def _tested(
        self, columns: list[TimelineColumn], rows: Iterable[Sighting]
    ) -> Tested:
        rows = list(rows)
        hosts = {row.host.lower() for row in rows if row.host}
        tested = Tested()
        if not hosts:
            return tested
        scanned = await self.session.execute(
            select(ScanSurfaceItem.scan_id, ScanSurfaceItem.host, ScanSurfaceItem.port)
            .where(
                ScanSurfaceItem.scan_id.in_([c.scan.id for c in columns]),
                ScanSurfaceItem.state.in_(SCANNED_STATES),
                func.lower(ScanSurfaceItem.host).in_(hosts),
            )
            .distinct()
        )
        for scan_id, host, port in scanned.all():
            found = tested.scanned.setdefault(scan_id, set())
            found.add(Locator(host.lower(), port))
            found.add(Locator(host.lower(), None))
        tested.selected = await self._selected(columns, rows)
        return tested

    async def _selected(
        self, columns: list[TimelineColumn], rows: list[Sighting]
    ) -> dict[int, set[str]]:
        """Per column: the finding checks the run selected and could send."""
        from stages.dast_scan.config import DastScanConfig  # noqa: PLC0415
        from stages.vulnerability_scan.config import (  # noqa: PLC0415
            VulnerabilityScanConfig,
        )

        plain = {
            r.template_id
            for r in rows
            if r.scanner == Scanner.NUCLEI.value and DAST_TAG not in (r.tags or [])
        }
        fuzzed = {
            r.template_id
            for r in rows
            if r.scanner == Scanner.NUCLEI.value and DAST_TAG in (r.tags or [])
        }
        unheard = await self._unheard([c.scan.id for c in columns if c.strict])
        out: dict[int, set[str]] = {}
        cache: dict[str, set[str]] = {}
        for col in columns:
            if not col.strict or not (plain or fuzzed):
                out[col.ord] = set()
                continue
            configs = (col.scan.execution_config or {}).get("stages") or {}
            cfg = _stage_config(
                VulnerabilityScanConfig, configs, VULN_STAGE, col.statuses
            )
            dast = _stage_config(DastScanConfig, configs, DAST_STAGE, col.statuses)
            heard = col.scan.id not in unheard
            key = json.dumps(
                [
                    cfg.model_dump(mode="json") if cfg else None,
                    dast.model_dump(mode="json") if dast else None,
                    heard,
                ],
                sort_keys=True,
                default=str,
            )
            if key not in cache:
                cache[key] = await self._select(cfg, dast, plain, fuzzed, heard)
            out[col.ord] = cache[key]
        return out

    async def _select(self, cfg, dast, plain: set[str], fuzzed: set[str], heard: bool):
        columns = (VulnTemplate.template_id, VulnTemplate.needs_oast, VulnTemplate.tags)
        rows: list = []
        if plain and cfg is not None and Scanner.NUCLEI.value in cfg.scanners:
            selection = cfg.selection()
            wanted = VulnTemplate.template_id.in_(sorted(plain))
            rows += (
                await self.session.execute(
                    select(*columns).where(selection_predicate(selection), wanted)
                )
            ).all()
            if selection.custom_templates:
                rows += (
                    await self.session.execute(
                        select(*columns).where(picked_predicate(selection), wanted)
                    )
                ).all()
        if fuzzed and dast is not None and Scanner.NUCLEI.value in dast.scanners:
            rows += (
                await self.session.execute(
                    select(*columns).where(
                        dast_predicate(dast.severities, headless=dast.headless),
                        VulnTemplate.template_id.in_(sorted(fuzzed)),
                    )
                )
            ).all()
        return {row.template_id for row in rows if heard or not wants_callback(row)}

    async def _unheard(self, scan_ids: list[UUID]) -> set[UUID]:
        from shared.definitions.oast import OAST_COVERAGE_GROUP  # noqa: PLC0415
        from shared.definitions.vulnerabilities import CoverageStatus  # noqa: PLC0415

        if not scan_ids:
            return set()
        rows = await self.session.execute(
            select(VulnerabilityCoverage.scan_id)
            .where(
                VulnerabilityCoverage.scan_id.in_(scan_ids),
                VulnerabilityCoverage.group == OAST_COVERAGE_GROUP,
                VulnerabilityCoverage.status == CoverageStatus.SKIPPED.value,
            )
            .distinct()
        )
        return set(rows.scalars().all())

    async def _new(self, scan: Scan, fingerprints: list[str]) -> set[str]:
        rows = await self.session.execute(
            select(Vulnerability.fingerprint).where(
                Vulnerability.scan_id == scan.id,
                Vulnerability.fingerprint.in_(fingerprints),
                preds.vuln_is_new(QueryScope((scan.id,), project_id=scan.project_id)),
            )
        )
        return set(rows.scalars().all())

    async def _first_seen(
        self, scan: Scan, column, values: list[str]
    ) -> dict[str, datetime]:
        rows = await self.session.execute(
            select(column, func.min(Vulnerability.discovered_at))
            .where(Vulnerability.target_id == scan.target_id, column.in_(values))
            .group_by(column)
        )
        return dict(rows.all())

    async def _coverage(self, columns: list[TimelineColumn]) -> dict[UUID, int]:
        rows = await self.session.execute(
            select(
                VulnerabilityCoverage.scan_id,
                func.max(VulnerabilityCoverage.templates_selected),
            )
            .where(VulnerabilityCoverage.scan_id.in_([c.scan.id for c in columns]))
            .group_by(VulnerabilityCoverage.scan_id)
        )
        return {scan_id: n for scan_id, n in rows.all() if n is not None}

    async def _origins(self, columns: list[TimelineColumn]) -> dict[UUID, int]:
        rows = await self.session.execute(
            select(ScanSurfaceItem.scan_id, func.count())
            .where(
                ScanSurfaceItem.scan_id.in_([c.scan.id for c in columns]),
                ScanSurfaceItem.class_ == SurfaceClass.ROOT.value,
                ScanSurfaceItem.state.in_(SCANNED_STATES),
            )
            .group_by(ScanSurfaceItem.scan_id)
        )
        return dict(rows.all())

    # ---------- lifespans ----------

    async def _lifespans(
        self,
        scan: Scan,
        scope: QueryScope,
        columns: list[TimelineColumn],
        history: dict[str, dict[int, Sighting]],
        newest: dict[str, Sighting],
        triage: dict[str, str],
        tested: Tested,
        f: FindingTimelineFilter,
    ) -> FindingTimelineResult:
        fingerprints = list(history)
        new = await self._new(scan, fingerprints)
        first_seen = await self._first_seen(
            scan, Vulnerability.fingerprint, fingerprints
        )
        viewed_at = _started(columns[-1])
        lives = [
            self._life(
                fp,
                history[fp],
                newest[fp],
                columns,
                tested,
                triage[fp],
                fp in new,
                first_seen.get(fp),
                viewed_at,
            )
            for fp in fingerprints
        ]
        counts = dict.fromkeys(FINDING_GROUP_ORDER, 0)
        for life in lives:
            counts[life.group] += 1
        counts[ALL] = len(lives)
        shown = [life for life in lives if f.flag is None or life.group == f.flag.value]
        shown = self._ordered(shown, f)
        page = shown[f.offset : f.offset + f.limit]
        reads = await self._reads(scope, page)
        items = [
            FindingLifespan(
                finding=reads[life.newest.id],
                group=life.group,
                state=life.state,
                cells=[FindingCell(state=s) for s in life.cells],
                segments=life.segments,
                first_seen_at=life.first_seen_at,
                open_since=life.open_since,
                open_days=life.open_days,
                fixed_at=life.fixed_at,
                fixed_scan_id=self._at(columns, life.fixed_ord),
                regressions=life.regressions,
                returned_at=_started(columns[life.returned_ord])
                if life.returned_ord is not None
                else None,
                returned_scan_id=self._at(columns, life.returned_ord),
                not_tested_runs=life.not_tested_runs,
                tested_runs=life.tested_runs,
                is_new=life.is_new,
                triage_state=life.triage_state,
                last_change_scan_id=self._at(columns, life.last_change_ord),
            )
            for life in page
            if life.newest.id in reads
        ]
        stats = await self._stats(columns, lives)
        return FindingTimelineResult(
            stats=stats,
            items=items,
            total=counts.get(f.flag.value if f.flag else ALL, 0),
            counts=counts,
        )

    async def _reads(self, scope: QueryScope, page: list[Life]) -> dict:
        ids = [life.newest.id for life in page]
        if not ids:
            return {}
        rows = (
            (
                await self.session.execute(
                    select(Vulnerability).where(Vulnerability.id.in_(ids))
                )
            )
            .scalars()
            .all()
        )
        by_id = {row.id: row for row in rows}
        by_scan: dict[UUID, list[Vulnerability]] = defaultdict(list)
        for i in ids:
            if i in by_id:
                by_scan[by_id[i].scan_id].append(by_id[i])
        service = VulnerabilityService(self.session)
        out = {}
        for scan_id, group in by_scan.items():
            one = QueryScope((scan_id,), project_id=scope.project_id)
            for read in await service.reads(one, group):
                out[read.id] = read
        return out

    @staticmethod
    def _life(
        fingerprint: str,
        rows: dict[int, Sighting],
        newest: Sighting,
        columns: list[TimelineColumn],
        tested: Tested,
        triage_state: str,
        is_new: bool,
        first_seen_at: datetime | None,
        viewed_at: datetime,
    ) -> Life:
        first = min(rows)
        cells, tested_runs = _cells(rows, newest, columns, tested)
        last_present = max(rows)
        later_fixed = [
            c.ord for c in columns if c.ord > last_present and cells[c.ord] == FIXED
        ]
        fixed_ord = later_fixed[0] if later_fixed else None
        fixed_at = _started(columns[fixed_ord]) if fixed_ord is not None else None
        stretch = max((o for o in rows if cells[o] == REGRESSED), default=first)
        open_since = _started(columns[stretch])
        preceded = any(c.observed for c in columns if c.ord < first)
        if stretch == first and not preceded and first_seen_at is not None:
            open_since = min(open_since, first_seen_at)
        regressed = [o for o, s in enumerate(cells) if s == REGRESSED]
        state = cells[-1]
        return Life(
            fingerprint=fingerprint,
            newest=newest,
            cells=cells,
            segments=_segments(cells, columns, viewed_at),
            group=_group(triage_state, bool(regressed), is_new, state, fixed_ord),
            state=state,
            open_since=open_since,
            open_days=_days(open_since, fixed_at or viewed_at),
            fixed_at=fixed_at,
            fixed_ord=fixed_ord,
            regressions=len(regressed),
            returned_ord=regressed[-1] if regressed else None,
            not_tested_runs=len(columns) - 1 - last_present if fixed_ord is None else 0,
            tested_runs=tested_runs,
            is_new=is_new,
            triage_state=triage_state,
            first_seen_at=first_seen_at,
            last_change_ord=_last_change(cells, first),
        )

    @staticmethod
    def _ordered(lives: list[Life], f: FindingTimelineFilter) -> list[Life]:
        """Sections in group order, the chosen sort inside each."""
        rank = {group: i for i, group in enumerate(FINDING_GROUP_ORDER)}

        def primary(life: Life):
            if f.sort == FindingSort.LAST_CHANGE.value:
                return life.last_change_ord or 0
            if f.sort == FindingSort.SEVERITY.value:
                return severity_rank(life.newest.severity)
            if f.sort == FindingSort.FIRST_SEEN.value:
                stamp = life.first_seen_at or life.open_since
                return stamp.timestamp() if stamp else 0.0
            if f.sort == FindingSort.NAME.value:
                return life.newest.template_name.lower()
            return life.open_days or 0

        out = sorted(
            lives,
            key=lambda life: (
                severity_rank(life.newest.severity),
                -(life.open_days or 0),
                life.newest.template_name.lower(),
                life.fingerprint,
            ),
        )
        out.sort(key=primary, reverse=f.order == "desc")
        out.sort(key=lambda life: rank[life.group])
        return out

    async def _stats(
        self, columns: list[TimelineColumn], lives: list[Life]
    ) -> FindingStats:
        coverage = await self._coverage(columns)
        origins = await self._origins(columns)
        counted = [life for life in lives if life.group != FindingGroup.SET_ASIDE.value]
        points: list[RunPoint] = []
        for col in columns:
            point = RunPoint(
                scan_id=col.scan.id,
                tested_checks=coverage.get(col.scan.id),
                tested_origins=origins.get(col.scan.id),
            )
            for life in counted:
                s = life.cells[col.ord]
                if s in PRESENT_STATES:
                    sev = life.newest.severity
                    point.open[sev] = point.open.get(sev, 0) + 1
                if s == REGRESSED:
                    point.regressed += 1
                if (
                    s == FIXED
                    and _previous_class(life.cells, col.ord) in PRESENT_STATES
                ):
                    point.fixed += 1
            points.append(point)
        last = columns[-1]
        open_now = sum(points[-1].open.values()) if last.observed else None
        earlier = [c for c in columns if c.ord < last.ord and c.observed]
        delta = (
            open_now - sum(points[earlier[-1].ord].open.values())
            if earlier and open_now is not None
            else None
        )
        fixed_days = [
            life.open_days
            for life in lives
            if life.group == FindingGroup.FIXED.value and life.open_days is not None
        ]
        standing = [life for life in counted if life.state != FIXED]
        oldest = max(standing, key=lambda life: life.open_days or 0, default=None)
        return FindingStats(
            open_now=open_now,
            open_delta=delta,
            untested=sum(
                1 for life in counted if life.state in (NOT_TESTED, UNOBSERVED)
            ),
            regressed=sum(
                1 for life in lives if life.group == FindingGroup.REGRESSED.value
            ),
            fixed=len(fixed_days),
            fixed_median_days=int(median(fixed_days)) if fixed_days else None,
            oldest_open_days=oldest.open_days if oldest else None,
            oldest_open_name=oldest.newest.template_name if oldest else None,
            oldest_open_severity=oldest.newest.severity if oldest else None,
            runs=points,
        )

    # ---------- by check ----------

    async def _by_check(
        self,
        scan: Scan,
        columns: list[TimelineColumn],
        history: dict[str, dict[int, Sighting]],
        newest: dict[str, Sighting],
        triage: dict[str, str],
        tested: Tested,
        f: FindingTimelineFilter,
    ) -> FindingTimelineResult:
        hosts: dict[str, dict[int, dict[str, Locator]]] = defaultdict(
            lambda: defaultdict(dict)
        )
        heads: dict[str, Sighting] = {}
        for fp, rows in history.items():
            if triage[fp] in SUPPRESSED_STATES:
                continue
            head = newest[fp]
            for ord_, row in rows.items():
                hosts[row.template_id][ord_][_host_key(row)] = _locator(row)
            if (
                head.template_id not in heads
                or head.discovered_at > heads[head.template_id].discovered_at
            ):
                heads[head.template_id] = head
        templates = sorted(hosts)
        if not templates:
            counts = dict.fromkeys((flag.value for flag in CheckFlag), 0)
            return FindingTimelineResult(
                check_stats=CheckStats(), counts={**counts, ALL: 0}
            )
        created = await self._library_dates(templates)
        first_seen = await self._first_seen(scan, Vulnerability.template_id, templates)
        coverage = await self._coverage(columns)
        rows = [
            self._check_row(
                tid,
                hosts[tid],
                heads[tid],
                columns,
                tested,
                created.get(tid),
                first_seen.get(tid),
            )
            for tid in templates
        ]
        counts = dict.fromkeys((flag.value for flag in CheckFlag), 0)
        for row in rows:
            for flag in row.flags:
                counts[flag] += 1
        counts[ALL] = len(rows)
        shown = [r for r in rows if f.flag is None or f.flag.value in r.flags]
        shown = self._ordered_checks(shown, columns, f)
        stats = CheckStats(
            checks=len(rows),
            tested_checks=coverage.get(columns[-1].scan.id),
            spread=counts[CheckFlag.SPREAD.value],
            shrank=counts[CheckFlag.SHRANK.value],
            cleared=counts[CheckFlag.CLEARED.value],
            library_new=counts[CheckFlag.LIBRARY_NEW.value],
        )
        return FindingTimelineResult(
            check_stats=stats,
            checks=shown[f.offset : f.offset + f.limit],
            total=counts.get(f.flag.value if f.flag else ALL, 0),
            counts=counts,
        )

    async def _library_dates(self, templates: list[str]) -> dict[str, datetime]:
        rows = await self.session.execute(
            select(VulnTemplate.template_id, func.min(VulnTemplate.created_at))
            .where(VulnTemplate.template_id.in_(templates))
            .group_by(VulnTemplate.template_id)
        )
        return dict(rows.all())

    @staticmethod
    def _check_row(
        template_id: str,
        by_ord: dict[int, dict[str, Locator]],
        head: Sighting,
        columns: list[TimelineColumn],
        tested: Tested,
        created_at: datetime | None,
        first_seen_at: datetime | None,
    ) -> CheckRow:
        cells, library_ord, last_change, carried = _check_cells(
            template_id, by_ord, columns, tested, created_at
        )
        judged = cells[-1].state == CheckState.TESTED.value
        now = cells[-1].hosts if judged else None
        peak = max(c.hosts for c in cells)
        found = [c for c in cells if c.state == CheckState.TESTED.value and c.hosts]
        baseline = found[0].hosts if found else None
        flags: list[str] = []
        if now is not None and baseline and now > baseline:
            flags.append(CheckFlag.SPREAD.value)
        if now is not None and baseline is not None and 0 < now < baseline:
            flags.append(CheckFlag.SHRANK.value)
        if now == 0 and peak > 0 and not carried:
            flags.append(CheckFlag.CLEARED.value)
        if library_ord:
            flags.append(CheckFlag.LIBRARY_NEW.value)
        return CheckRow(
            template_id=template_id,
            template_name=head.template_name,
            severity=head.severity,
            is_kev=head.is_kev,
            cells=cells,
            flags=flags,
            hosts_now=now,
            peak=peak,
            library_scan_id=columns[library_ord].scan.id if library_ord else None,
            first_seen_at=first_seen_at,
            last_change_scan_id=columns[last_change].scan.id
            if last_change is not None
            else None,
        )

    @staticmethod
    def _ordered_checks(
        rows: list[CheckRow], columns: list[TimelineColumn], f: FindingTimelineFilter
    ) -> list[CheckRow]:
        ord_of = {col.scan.id: col.ord for col in columns}

        def primary(row: CheckRow):
            if f.sort == CheckSort.SEVERITY.value:
                return severity_rank(row.severity)
            if f.sort == CheckSort.LAST_CHANGE.value:
                return ord_of.get(row.last_change_scan_id, -1)
            if f.sort == CheckSort.NAME.value:
                return row.template_name.lower()
            return -1 if row.hosts_now is None else row.hosts_now

        out = sorted(
            rows,
            key=lambda row: (
                severity_rank(row.severity),
                -(row.hosts_now or 0),
                row.template_id,
            ),
        )
        out.sort(key=primary, reverse=f.order == "desc")
        return out


def _cells(
    rows: dict[int, Sighting],
    newest: Sighting,
    columns: list[TimelineColumn],
    tested: Tested,
) -> tuple[list[str], int]:
    """One state per column and the runs that tested for the finding."""
    first = min(rows)
    cells: list[str] = []
    since_fixed = False
    tested_runs = 0
    for col in columns:
        if col.ord < first:
            cells.append(UNSEEN)
            tested_runs += int(tested.covers(col, newest))
        elif col.ord in rows:
            cells.append(REGRESSED if since_fixed else OPEN)
            since_fixed = False
            tested_runs += 1
        elif not col.observed:
            cells.append(UNOBSERVED)
        elif tested.covers(col, newest):
            cells.append(FIXED)
            since_fixed = True
            tested_runs += 1
        else:
            cells.append(NOT_TESTED)
    return cells, tested_runs


def _group(
    triage_state: str, regressed: bool, is_new: bool, state: str, fixed_ord: int | None
) -> str:
    if triage_state in SUPPRESSED_STATES:
        return FindingGroup.SET_ASIDE.value
    if fixed_ord is not None:
        return FindingGroup.FIXED.value
    if regressed:
        return FindingGroup.REGRESSED.value
    if is_new and state in PRESENT_STATES:
        return FindingGroup.NEW.value
    return FindingGroup.OPEN.value


def _last_change(cells: list[str], first: int) -> int:
    """The last column where the finding moved between present and fixed."""
    last = first
    previous = OPEN
    for ord_, s in enumerate(cells):
        if ord_ <= first or s in (UNSEEN, UNOBSERVED, NOT_TESTED):
            continue
        kind = OPEN if s in PRESENT_STATES else s
        if kind != previous:
            last = ord_
            previous = kind
    return last


def _check_cells(
    template_id: str,
    by_ord: dict[int, dict[str, Locator]],
    columns: list[TimelineColumn],
    tested: Tested,
    created_at: datetime | None,
) -> tuple[list[CheckCell], int | None, int | None, set[str]]:
    """Hosts per column, the library column, the last change, the hosts the viewed run did not judge."""
    known: dict[str, Locator] = {}
    for found in by_ord.values():
        known.update(found)
    cells: list[CheckCell] = []
    previous: set[str] | None = None
    library_ord: int | None = None
    last_change: int | None = None
    carried: set[str] = set()
    for col in columns:
        found = set(by_ord.get(col.ord, {}))
        in_library = created_at is None or _started(col) >= created_at
        if in_library and library_ord is None and created_at is not None:
            library_ord = col.ord
        scanned = tested.scanned.get(col.scan.id, set())
        judged = {key for key, loc in known.items() if _covered(loc, scanned)}
        selected = template_id in tested.selected.get(col.ord, ())
        state = _check_state(col, found, in_library, selected and bool(judged))
        cell = CheckCell(state=state, hosts=len(found))
        if state == CheckState.TESTED.value:
            carried = {key for key in (previous or set()) if key not in judged} - found
            if previous is not None:
                added = sorted(found - previous)
                removed = sorted((previous - found) & judged)
                cell.delta = len(added) - len(removed)
                cell.added = added[:MAX_CELL_HOSTS]
                cell.removed = removed[:MAX_CELL_HOSTS]
                cell.more = max(0, len(added) + len(removed) - MAX_CELL_HOSTS * 2)
                if added or removed:
                    last_change = col.ord
            elif found:
                last_change = col.ord
            previous = found | carried
        cells.append(cell)
    return cells, library_ord, last_change, carried


def _covered(loc: Locator, scanned: set[Locator]) -> bool:
    return loc in scanned or Locator(loc.host, None) in scanned


def _check_state(
    col: TimelineColumn, found: set[str], in_library: bool, selected: bool
) -> str:
    if found:
        return CheckState.TESTED.value
    if not in_library:
        return CheckState.NOT_IN_LIBRARY.value
    if not col.observed:
        return CheckState.UNOBSERVED.value
    if col.strict and selected:
        return CheckState.TESTED.value
    return CheckState.NOT_TESTED.value


def _host_key(row: Sighting) -> str:
    host = row.host or row.ip or ""
    return f"{host}:{row.port}" if row.port and host else host


def _locator(row: Sighting) -> Locator:
    return Locator((row.host or row.ip or "").lower(), row.port or None)


def _flag_for_mode(f: FindingTimelineFilter) -> FindingTimelineFilter:
    checks = f.mode == FindingTimelineMode.CHECKS
    if f.flag is None or isinstance(f.flag, CheckFlag) == checks:
        return f
    return f.model_copy(update={"flag": None})


def _previous_class(cells: list[str], ord_: int) -> str | None:
    for s in reversed(cells[:ord_]):
        if s in (UNSEEN, UNOBSERVED, NOT_TESTED):
            continue
        return OPEN if s in PRESENT_STATES else s
    return None


def _segments(
    cells: list[str], columns: list[TimelineColumn], viewed_at: datetime
) -> list[LifeSegment]:
    segments: list[LifeSegment] = []
    for ord_, state in enumerate(cells):
        if state == UNSEEN:
            continue
        if segments and segments[-1].state == state:
            segments[-1].end = ord_
        else:
            segments.append(LifeSegment(state=state, start=ord_, end=ord_))
    for i, seg in enumerate(segments):
        end_at = (
            _started(columns[segments[i + 1].start])
            if i + 1 < len(segments)
            else viewed_at
        )
        seg.days = _days(_started(columns[seg.start]), end_at)
    return segments


__all__ = ["FindingTimelineService"]
