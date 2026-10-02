"""What is new in a project since a point in time, grouped by the run or program it came from."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import (
    DateTime,
    Uuid,
    cast,
    column,
    exists,
    func,
    literal,
    not_,
    or_,
    select,
    values,
)
from sqlalchemy.dialects.postgresql import BIT
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from shared.definitions.bounty_programs import (
    ASSET_TYPES_BY_KEY,
    UNKNOWN_ASSET_TYPE,
    ScopeState,
    event_spec,
)
from shared.definitions.vulnerabilities import (
    ALERT_SEVERITIES,
    SEVERITY_RANK,
)
from shared.definitions.watch import ARRIVED_STATES, CT_SOURCE, WatchHostState
from shared.definitions.whats_new import (
    BOUNTY_ROWS_PER_SECTION,
    DEFAULT_NEW_WINDOW,
    DEFAULT_ZONE,
    ENGAGED_EVENTS,
    EVENT_KIND,
    EVIDENCE_FINDINGS,
    GRID_DAYS,
    GROUP_LIMIT,
    KIND_ORDER,
    NEW_WINDOWS,
    PROGRAM_EVENTS,
    SCOPE_SOURCE,
    SOURCE_LABELS,
    TERMS_KINDS,
    VISUAL_DISTANCE,
    VISUAL_FIELDS,
    VISUAL_LIMIT,
    WATCH_SOURCE,
    Fact,
    NewBasis,
    NewKind,
    NewTone,
    ProgramRing,
    SubjectKind,
    mark_key,
)
from shared.enums.scan import SCAN_TERMINAL_STATUSES, ScanStatus
from shared.models.bounty_program import BountyEventRow, BountyProgram, BountyScope
from shared.models.scan import Scan
from shared.models.subdomain import Subdomain
from shared.models.target import Target, TargetOrganization
from shared.models.vulnerability import Vulnerability
from shared.models.watch import ProgramWatch, UserMark, WatchHost
from shared.models.whats_new import (
    NewDay,
    NewEvidence,
    NewFeed,
    NewGroup,
    NewItem,
    NewSection,
    NewSubject,
    VisualFeed,
    VisualPair,
)
from shared.services.asset_query import vuln_seen_earlier, vuln_suppressed
from shared.services.asset_query.tokens import token
from shared.services.scan_scope import census_only
from shared.utils.datetime import utc_now


def _new_conds(baseline: list[UUID]) -> list:
    return [
        Vulnerability.scan_id.in_(baseline),
        Vulnerability.severity.in_(ALERT_SEVERITIES),
        not_(vuln_seen_earlier()),
        not_(vuln_suppressed(tuple(baseline))),
    ]


def _finding_text(q: str):
    return _text_match(
        (Vulnerability.template_name, Vulnerability.template_id, Vulnerability.host),
        q,
    )


def _text_match(columns, q: str):
    needle = f"%{q}%"
    return or_(*[c.ilike(needle) for c in columns])


def _eligibility(scope) -> str | None:
    if scope is None or scope.eligible_for_bounty is None:
        return None
    return (
        "Eligible for bounty"
        if scope.eligible_for_bounty
        else "Not eligible for bounty"
    )


def _source_label(source: str | None) -> str | None:
    return SOURCE_LABELS.get(source, source) if source else None


def _visual_value(value):
    if isinstance(value, list):
        return sorted(str(v) for v in value)
    return value or None


def _day_start(d: date, zone: ZoneInfo) -> datetime:
    return datetime.combine(d, time.min, tzinfo=zone)


def _day_of(at: datetime, zone: ZoneInfo) -> str:
    return at.astimezone(zone).date().isoformat()


def _local_date(column, zone: ZoneInfo):
    return func.date(func.timezone(literal(zone.key, literal_execute=True), column))


class _Check:
    def __init__(self, template_id: str):
        self.template_id = template_id
        self.name: str | None = None
        self.kev = 0
        self.severities: dict[str, int] = defaultdict(int)
        self.runs: dict[UUID, int] = defaultdict(int)
        self.kev_runs: dict[UUID, int] = defaultdict(int)

    def rank(self):
        worst = min(
            (SEVERITY_RANK.get(sev, len(SEVERITY_RANK)) for sev in self.severities),
            default=len(SEVERITY_RANK),
        )
        return (worst, -self.kev, -sum(self.runs.values()), self.name or "")


class _Groups:
    def __init__(self, zone: ZoneInfo):
        self.zone = zone
        self.by_id: dict[str, NewGroup] = {}
        self.counts: dict[str, int] = dict.fromkeys(KIND_ORDER, 0)
        self.facts: dict[str, dict[str, int]] = defaultdict(dict)
        self.daily: dict[str, dict[str, int]] = defaultdict(dict)
        self.visual = 0
        self.checks: dict[str, _Check] = {}

    def check(self, template_id: str) -> _Check:
        c = self.checks.get(template_id)
        if c is None:
            c = self.checks[template_id] = _Check(template_id)
        return c

    def group(self, gid: str, subject: NewSubject, at: datetime) -> NewGroup:
        g = self.by_id.get(gid)
        if g is None:
            g = NewGroup(id=gid, subject=subject, at=at)
            self.by_id[gid] = g
        elif at > g.at:
            g.at = at
        return g

    def section(self, g: NewGroup, kind: str, total: int, items: list[NewItem]):
        if total <= 0:
            return
        g.sections.append(NewSection(kind=kind, total=total, items=items))
        g.counts[kind] = g.counts.get(kind, 0) + total

    def count(self, kind: str, n: int):
        self.counts[kind] = self.counts.get(kind, 0) + n

    def fact(self, kind: str, fact: str, n: int):
        if n:
            self.facts[kind][fact] = self.facts[kind].get(fact, 0) + n

    def day(self, kind: str, d: date | str, n: int):
        key = d.isoformat() if isinstance(d, date) else str(d)[:10]
        self.daily[key][kind] = self.daily[key].get(kind, 0) + int(n)


class WhatsNewService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ---------- marks ----------

    async def mark(self, user_id: UUID, project_id: UUID) -> datetime | None:
        return await self.session.scalar(
            select(UserMark.marked_at).where(
                UserMark.user_id == user_id, UserMark.key == mark_key(project_id)
            )
        )

    async def mark_seen(self, user_id: UUID, project_id: UUID) -> datetime:
        now = utc_now()
        stmt = pg_insert(UserMark).values(
            user_id=user_id, key=mark_key(project_id), marked_at=now
        )
        await self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=["user_id", "key"], set_={"marked_at": now}
            )
        )
        await self.session.commit()
        return now

    # ---------- feed ----------

    async def feed(
        self,
        project_id: UUID,
        user_id: UUID,
        *,
        since: datetime | None = None,
        window: str | None = None,
        day_from: date | None = None,
        day_to: date | None = None,
        target_id: UUID | None = None,
        platform: str | None = None,
        handle: str | None = None,
        kinds: set[str] | None = None,
        ring: str = ProgramRing.ENGAGED.value,
        q: str | None = None,
        bounty: bool = True,
        grid: bool = True,
        visual: bool = True,
        tz: str = DEFAULT_ZONE,
    ) -> NewFeed:
        now = utc_now()
        zone = ZoneInfo(tz)
        marked_at = await self.mark(user_id, project_id)
        basis, cutoff, until, window = self._period(
            now, marked_at, since, window, day_from, day_to, zone
        )

        grid_start = _day_start(
            now.astimezone(zone).date() - timedelta(days=GRID_DAYS - 1), zone
        )
        range_start = min(cutoff, grid_start) if grid else cutoff
        wanted = set(kinds) if kinds else set(KIND_ORDER)
        q = (q or "").strip() or None

        program = await self._program(platform, handle) if bounty else None
        out = _Groups(zone)
        if platform and handle and program is None:
            return NewFeed(
                since=cutoff,
                until=until,
                basis=basis,
                marked_at=marked_at,
                window=window if basis == NewBasis.WINDOW.value else None,
                counts=out.counts,
                daily=self._days(grid_start, now, out.daily, zone) if grid else [],
            )
        target_ids = await self._target_ids(project_id, target_id, program)
        target_value = await self._target_value(project_id, target_id)

        await self._runs(
            out,
            project_id,
            cutoff,
            until,
            range_start,
            grid_start if grid else None,
            target_ids,
            wanted,
            q,
        )
        if visual:
            out.visual = await self._visual_count(
                project_id, cutoff, until, target_ids, q
            )
        if bounty:
            await self._bounty(
                out,
                project_id,
                cutoff,
                until,
                grid_start if grid else None,
                target_ids,
                target_value,
                program,
                ring,
                wanted,
                q,
            )

        groups = sorted(
            (g for g in out.by_id.values() if g.sections),
            key=lambda g: g.at,
            reverse=True,
        )
        truncated = len(groups) > GROUP_LIMIT
        self._evidence(out, groups)
        return NewFeed(
            since=cutoff,
            until=until,
            basis=basis,
            marked_at=marked_at,
            window=window if basis == NewBasis.WINDOW.value else None,
            counts=out.counts,
            facts=dict(out.facts),
            daily=self._days(grid_start, now, out.daily, zone) if grid else [],
            groups=groups[:GROUP_LIMIT],
            events=len(groups),
            truncated=truncated,
            visual=out.visual,
        )

    @staticmethod
    def _period(now, marked_at, since, window, day_from, day_to, zone: ZoneInfo):
        until: datetime | None = None
        if day_from is not None:
            basis = NewBasis.DAYS.value
            cutoff = _day_start(day_from, zone)
            until = _day_start((day_to or day_from) + timedelta(days=1), zone)
        elif since is not None:
            basis, cutoff = NewBasis.MARK.value, since
        elif window:
            basis, cutoff = NewBasis.WINDOW.value, now - NEW_WINDOWS[window]
        elif marked_at is not None:
            basis, cutoff = NewBasis.MARK.value, marked_at
        else:
            window = DEFAULT_NEW_WINDOW
            basis, cutoff = NewBasis.WINDOW.value, now - NEW_WINDOWS[window]
        return basis, cutoff, until, window

    async def unseen(
        self, project_id: UUID, user_id: UUID, *, bounty: bool, tz: str = DEFAULT_ZONE
    ) -> int:
        feed = await self.feed(
            project_id, user_id, bounty=bounty, grid=False, visual=False, tz=tz
        )
        return feed.events

    @staticmethod
    def _days(start: datetime, now: datetime, daily, zone: ZoneInfo) -> list[NewDay]:
        day = start.astimezone(zone).date()
        end = now.astimezone(zone).date()
        out: list[NewDay] = []
        while day <= end:
            key = day.isoformat()
            out.append(NewDay(date=key, counts=daily.get(key, {})))
            day += timedelta(days=1)
        return out

    # ---------- scope ----------

    async def _program(self, platform: str | None, handle: str | None):
        if not platform or not handle:
            return None
        return await self.session.scalar(
            select(BountyProgram).where(
                BountyProgram.platform == platform, BountyProgram.handle == handle
            )
        )

    async def _target_value(self, project_id: UUID, target_id: UUID | None):
        if target_id is None:
            return None
        return await self.session.scalar(
            select(Target.target_value).where(
                Target.id == target_id, Target.project_id == project_id
            )
        )

    @staticmethod
    def _watched_programs(project_id: UUID):
        return select(ProgramWatch.program_id).where(
            ProgramWatch.project_id == project_id
        )

    @staticmethod
    def _covering_programs(project_id: UUID):
        return (
            select(BountyScope.program_id)
            .join(Target, Target.target_value == BountyScope.target_value)
            .where(Target.project_id == project_id)
        )

    def _engaged_programs(self, project_id: UUID):
        return self._watched_programs(project_id).union(
            self._covering_programs(project_id)
        )

    @staticmethod
    def _watch_targets(project_id: UUID, program_id: UUID | None = None):
        watches = select(ProgramWatch.organization_id).where(
            ProgramWatch.project_id == project_id,
            ProgramWatch.organization_id.is_not(None),
        )
        if program_id is not None:
            watches = watches.where(ProgramWatch.program_id == program_id)
        return (
            select(TargetOrganization.target_id)
            .join(Target, Target.id == TargetOrganization.target_id)
            .where(
                Target.project_id == project_id,
                TargetOrganization.organization_id.in_(watches),
            )
        )

    @staticmethod
    def _scope_targets(project_id: UUID, program_id: UUID | None = None):
        scopes = select(BountyScope.target_value).where(
            BountyScope.target_value.is_not(None)
        )
        if program_id is not None:
            scopes = scopes.where(BountyScope.program_id == program_id)
        return select(Target.id).where(
            Target.project_id == project_id, Target.target_value.in_(scopes)
        )

    async def _target_ids(
        self, project_id: UUID, target_id: UUID | None, program
    ) -> list[UUID] | None:
        if target_id is not None:
            return [target_id]
        if program is None:
            return None
        rows = await self.session.execute(
            self._scope_targets(project_id, program.id).union(
                self._watch_targets(project_id, program.id)
            )
        )
        return [r[0] for r in rows.all()]

    # ---------- runs ----------

    async def _runs(
        self,
        out: _Groups,
        project_id: UUID,
        since: datetime,
        until: datetime | None,
        range_start: datetime,
        grid_start: datetime | None,
        target_ids,
        wanted: set[str],
        q: str | None,
    ) -> None:
        conds = [
            Scan.project_id == project_id,
            census_only(),
            or_(Scan.completed_at.is_(None), Scan.completed_at >= range_start),
        ]
        if target_ids is not None:
            conds.append(Scan.target_id.in_(target_ids))
        scans = {
            s.id: s
            for s in (await self.session.execute(select(Scan).where(*conds)))
            .scalars()
            .all()
        }
        if not scans:
            return
        baseline = await self._baseline_scans(scans)
        if not baseline:
            return
        kind = NewKind.FINDING.value
        base = _new_conds(baseline)
        stmt = (
            select(
                Vulnerability.scan_id,
                Vulnerability.template_id,
                Vulnerability.severity,
                func.max(Vulnerability.template_name),
                func.count(),
                func.count().filter(Vulnerability.is_kev),
                func.max(Vulnerability.discovered_at),
            )
            .where(*base)
            .group_by(
                Vulnerability.scan_id,
                Vulnerability.template_id,
                Vulnerability.severity,
            )
        )
        by_run: dict[UUID, list] = defaultdict(list)
        for row in (await self.session.execute(stmt)).all():
            by_run[row[0]].append(row)
        if q and by_run:
            matched = set(
                (
                    await self.session.execute(
                        select(Vulnerability.scan_id)
                        .where(*base, _finding_text(q))
                        .distinct()
                    )
                ).scalars()
            )
            by_run = {sid: r for sid, r in by_run.items() if sid in matched}
        if not by_run:
            return
        targets = {
            t.id: t
            for t in (
                await self.session.execute(
                    select(Target).where(
                        Target.id.in_({scans[sid].target_id for sid in by_run})
                    )
                )
            )
            .scalars()
            .all()
        }
        show = kind in wanted
        for sid, found in by_run.items():
            scan = scans[sid]
            at = scan.completed_at or max(r[6] for r in found)
            total = sum(r[4] for r in found)
            if grid_start is not None and at >= grid_start:
                day = _day_of(at, out.zone)
                out.day(kind, day, total)
                for r in found:
                    out.day(r[2], day, r[4])
            if at < since or (until is not None and at >= until):
                continue
            out.count(kind, total)
            g = (
                self._run_group(out, scan, targets[scan.target_id], at)
                if show
                else None
            )
            for _, template_id, severity, name, n, kev, _last in found:
                out.fact(kind, severity, n)
                out.fact(kind, Fact.KEV.value, kev)
                if g is None:
                    continue
                g.severities[severity] = g.severities.get(severity, 0) + n
                c = out.check(template_id)
                c.name = name
                c.kev += kev
                c.kev_runs[sid] += kev
                c.severities[severity] += n
                c.runs[sid] += n
            if g is not None:
                out.section(g, kind, total, [])
        if show:
            await self._previous_runs(out, scans)

    async def _visual_count(self, project_id, since, until, target_ids, q) -> int:
        pairs = await self._run_pairs(project_id, since, until, target_ids)
        if not pairs:
            return 0
        stmt = select(func.count()).select_from(self._pairs_source(pairs, q))
        return int(await self.session.scalar(stmt) or 0)

    # ---------- visual changes ----------

    async def _run_pairs(
        self, project_id: UUID, since, until, target_ids
    ) -> list[tuple[UUID, UUID]]:
        ordering = func.coalesce(Scan.started_at, Scan.created_at)
        conds = [
            Scan.project_id == project_id,
            census_only(),
            Scan.status.in_(SCAN_TERMINAL_STATUSES),
        ]
        if target_ids is not None:
            conds.append(Scan.target_id.in_(target_ids))
        ranked = (
            select(
                Scan.id.label("id"),
                ordering.label("at"),
                func.lag(Scan.id)
                .over(partition_by=Scan.target_id, order_by=ordering.asc())
                .label("prev_id"),
            )
            .where(*conds)
            .subquery()
        )
        window = [ranked.c.prev_id.is_not(None), ranked.c.at >= since]
        if until is not None:
            window.append(ranked.c.at < until)
        rows = await self.session.execute(
            select(ranked.c.id, ranked.c.prev_id).where(*window)
        )
        return [(r[0], r[1]) for r in rows.all()]

    @staticmethod
    def _pairs_join(pairs: list[tuple[UUID, UUID]], q: str | None):
        table = values(
            column("cur", Uuid), column("prev", Uuid), name="run_pairs"
        ).data(pairs)
        a = aliased(Subdomain)
        b = aliased(Subdomain)
        distance = func.bit_count(
            cast(a.screenshot_phash.op("#")(b.screenshot_phash), BIT(64))
        ).label("distance")
        conds = [
            a.screenshot_phash.is_not(None),
            b.screenshot_phash.is_not(None),
            a.screenshot_path.is_not(None),
            b.screenshot_path.is_not(None),
            distance > VISUAL_DISTANCE,
        ]
        if q:
            conds.append(a.name.ilike(f"%{q}%"))
        stmt = (
            select()
            .select_from(table)
            .join(a, a.scan_id == table.c.cur)
            .join(b, (b.scan_id == table.c.prev) & (b.name == a.name))
            .where(*conds)
        )
        return stmt, a, b, table.c.prev, distance

    @classmethod
    def _pairs_source(cls, pairs: list[tuple[UUID, UUID]], q: str | None):
        stmt, a, *_ = cls._pairs_join(pairs, q)
        return stmt.add_columns(a.id).subquery()

    async def visual(
        self,
        project_id: UUID,
        user_id: UUID,
        *,
        since: datetime | None = None,
        window: str | None = None,
        day_from: date | None = None,
        day_to: date | None = None,
        target_id: UUID | None = None,
        q: str | None = None,
        tz: str = DEFAULT_ZONE,
    ) -> VisualFeed:
        now = utc_now()
        marked_at = await self.mark(user_id, project_id)
        basis, cutoff, until, window = self._period(
            now, marked_at, since, window, day_from, day_to, ZoneInfo(tz)
        )
        q = (q or "").strip() or None
        target_ids = [target_id] if target_id is not None else None
        pairs = await self._run_pairs(project_id, cutoff, until, target_ids)
        feed = VisualFeed(
            since=cutoff,
            until=until,
            basis=basis,
            window=window if basis == NewBasis.WINDOW.value else None,
        )
        if not pairs:
            return feed
        stmt, a, b, prev_id, distance = self._pairs_join(pairs, q)
        rows = (
            await self.session.execute(
                stmt.add_columns(a, b, prev_id, distance, Target)
                .join(Target, Target.id == a.target_id)
                .order_by(distance.desc(), a.name)
                .limit(VISUAL_LIMIT + 1)
            )
        ).all()
        feed.truncated = len(rows) > VISUAL_LIMIT
        for cur, prev, prev_scan, dist, target in rows[:VISUAL_LIMIT]:
            moved = [
                field
                for field in VISUAL_FIELDS
                if _visual_value(getattr(cur, field))
                != _visual_value(getattr(prev, field))
            ]
            pair = VisualPair(
                id=f"visual:{cur.id}",
                host=cur.name,
                at=cur.discovered_at,
                distance=int(dist),
                before_path=prev.screenshot_path or "",
                after_path=cur.screenshot_path or "",
                before_status=prev.http_status,
                after_status=cur.http_status,
                before_title=prev.page_title,
                after_title=cur.page_title,
                before_tech=list(prev.tech or []),
                after_tech=list(cur.tech or []),
                before_server=prev.webserver,
                after_server=cur.webserver,
                moved=moved,
                silent=not moved,
                target_id=target.id,
                target_value=target.target_value,
                target_type=target.target_type.value,
                scan_id=cur.scan_id,
                previous_scan_id=prev_scan,
                query=f"host={cur.name}",
            )
            feed.pairs.append(pair)
            feed.silent += int(pair.silent)
        feed.total = len(feed.pairs)
        return feed

    async def _baseline_scans(self, scans: dict[UUID, Scan]) -> list[UUID]:
        """Scans holding findings, and those of them with an earlier scan that held findings."""
        firsts = (
            await self.session.execute(
                select(Vulnerability.scan_id, func.min(Vulnerability.discovered_at))
                .where(Vulnerability.scan_id.in_(list(scans)))
                .group_by(Vulnerability.scan_id)
            )
        ).all()
        if not firsts:
            return []
        table = values(
            column("id", Uuid),
            column("target_id", Uuid),
            column("first_at", DateTime(timezone=True)),
            name="firsts",
        ).data([(sid, scans[sid].target_id, at) for sid, at in firsts])
        earlier = aliased(Vulnerability)
        rows = await self.session.execute(
            select(table.c.id).where(
                exists(
                    select(1).where(
                        earlier.target_id == table.c.target_id,
                        earlier.scan_id != table.c.id,
                        earlier.discovered_at < table.c.first_at,
                    )
                )
            )
        )
        return [r[0] for r in rows.all()]

    @staticmethod
    def _evidence(out: _Groups, groups: list[NewGroup]) -> None:
        by_run: dict[UUID, list[_Check]] = defaultdict(list)
        for c in out.checks.values():
            for sid in c.runs:
                by_run[sid].append(c)
        for g in groups:
            if g.scan_id is None:
                continue
            ranked = sorted(by_run.get(g.scan_id, []), key=_Check.rank)
            picked = ranked[:EVIDENCE_FINDINGS]
            g.more = len(ranked) - len(picked)
            g.evidence = [
                NewEvidence(
                    kind=NewKind.FINDING.value,
                    label=c.name or c.template_id,
                    count=c.runs[g.scan_id],
                    severity=min(
                        c.severities,
                        key=lambda sev: SEVERITY_RANK.get(sev, len(SEVERITY_RANK)),
                        default=None,
                    ),
                    kev=c.kev_runs[g.scan_id],
                    query=f"is:new {token('template', '=', c.template_id)}",
                )
                for c in picked
            ]

    def _run_group(
        self, out: _Groups, scan: Scan, target: Target, at: datetime
    ) -> NewGroup:
        g = out.group(
            f"run:{scan.id}",
            NewSubject(
                kind=SubjectKind.RUN.value,
                id=str(scan.id),
                label=target.target_value,
                target_id=target.id,
                target_value=target.target_value,
                target_type=target.target_type.value,
            ),
            at,
        )
        g.scan_id = scan.id
        g.scan_started_at = scan.started_at or scan.created_at
        g.completed_at = scan.completed_at
        g.scan_status = scan.status
        return g

    async def _previous_runs(self, out: _Groups, scans) -> None:
        run_scans = [g.scan_id for g in out.by_id.values() if g.scan_id is not None]
        if not run_scans:
            return
        ordering = func.coalesce(Scan.started_at, Scan.created_at)
        prev_id = (
            func.lag(Scan.id)
            .over(partition_by=Scan.target_id, order_by=ordering.asc())
            .label("prev_id")
        )
        ranked = (
            select(Scan.id.label("id"), prev_id)
            .where(
                Scan.target_id.in_({scans[s].target_id for s in run_scans}),
                census_only(),
                Scan.status == ScanStatus.COMPLETED.value,
            )
            .subquery()
        )
        rows = await self.session.execute(
            select(ranked.c.id, ranked.c.prev_id).where(ranked.c.id.in_(run_scans))
        )
        previous = dict(rows.all())
        for g in out.by_id.values():
            if g.scan_id is not None:
                g.previous_scan_id = previous.get(g.scan_id)

    # ---------- bounty hub ----------

    async def _bounty(
        self,
        out: _Groups,
        project_id: UUID,
        since: datetime,
        until: datetime | None,
        grid_start: datetime | None,
        target_ids,
        target_value: str | None,
        program,
        ring: str,
        wanted: set[str],
        q: str | None,
    ) -> None:
        await self._events(
            out,
            project_id,
            since,
            until,
            grid_start,
            program,
            target_value,
            ring,
            wanted,
            q,
        )
        await self._hosts(
            out,
            project_id,
            since,
            until,
            grid_start,
            target_ids,
            program,
            wanted,
            q,
        )
        await self._targets(
            out, project_id, since, until, grid_start, target_ids, wanted, q
        )

    @staticmethod
    def _program_subject(e: BountyEventRow, watch_id: UUID | None) -> NewSubject:
        return NewSubject(
            kind=SubjectKind.PROGRAM.value,
            id=str(e.program_id),
            label=e.program_name,
            platform=e.platform,
            handle=e.handle,
            watched=watch_id is not None,
            watch_id=watch_id,
        )

    async def _watches(self, project_id: UUID) -> dict[UUID, UUID]:
        rows = await self.session.execute(
            select(ProgramWatch.program_id, ProgramWatch.id).where(
                ProgramWatch.project_id == project_id
            )
        )
        return dict(rows.all())

    def _event_reach(self, project_id: UUID, program, ring: str):
        engaged = BountyEventRow.program_id.in_(self._engaged_programs(project_id))
        scope_kinds = list(ENGAGED_EVENTS)
        if program is not None:
            return BountyEventRow.program_id == program.id
        if ring == ProgramRing.LIBRARY.value:
            return BountyEventRow.kind.in_(scope_kinds + list(PROGRAM_EVENTS))
        return or_(
            BountyEventRow.kind.in_(list(PROGRAM_EVENTS)),
            BountyEventRow.kind.in_(scope_kinds) & engaged,
        )

    async def _events(
        self,
        out: _Groups,
        project_id: UUID,
        since: datetime,
        until: datetime | None,
        grid_start: datetime | None,
        program,
        target_value: str | None,
        ring: str,
        wanted: set[str],
        q: str | None,
    ) -> None:
        base = [
            BountyEventRow.kind.in_(list(EVENT_KIND)),
            self._event_reach(project_id, program, ring),
        ]
        if target_value:
            base.append(
                BountyEventRow.asset_identifier.in_([target_value, f"*.{target_value}"])
            )
        if q:
            base.append(
                _text_match(
                    (BountyEventRow.asset_identifier, BountyEventRow.program_name), q
                )
            )

        if grid_start is not None:
            daily = await self.session.execute(
                select(
                    BountyEventRow.kind,
                    _local_date(BountyEventRow.created_at, out.zone),
                    func.count(),
                )
                .where(*base, BountyEventRow.created_at >= grid_start)
                .group_by(
                    BountyEventRow.kind,
                    _local_date(BountyEventRow.created_at, out.zone),
                )
            )
            for kind, d, n in daily.all():
                out.day(EVENT_KIND[kind], d, n)

        window = [*base, BountyEventRow.created_at >= since]
        if until is not None:
            window.append(BountyEventRow.created_at < until)
        counted = await self.session.execute(
            select(BountyEventRow.kind, func.count())
            .where(*window)
            .group_by(BountyEventRow.kind)
        )
        per_kind: dict[str, int] = defaultdict(int)
        for kind, n in counted.all():
            per_kind[EVENT_KIND[kind]] += int(n)
        for kind, n in per_kind.items():
            out.count(kind, n)
        if per_kind:
            await self._event_rows(out, project_id, window, wanted)

    async def _event_rows(self, out: _Groups, project_id: UUID, window, wanted):
        stmt = (
            select(BountyEventRow, BountyProgram)
            .join(BountyProgram, BountyProgram.id == BountyEventRow.program_id)
            .where(*window)
            .order_by(BountyEventRow.created_at.desc())
        )
        events = (await self.session.execute(stmt)).all()
        watches = await self._watches(project_id)
        scope_values = {
            e.asset_identifier
            for e, _ in events
            if e.asset_identifier and EVENT_KIND[e.kind] != NewKind.PROGRAM.value
        }
        scopes = await self._scope_rows({e.program_id for e, _ in events}, scope_values)
        existing = await self._existing_targets(
            project_id, {s.target_value for s in scopes.values() if s.target_value}
        )
        scanned = await self._scanned_targets(set(existing.values()))

        by_group: dict[str, dict[str, list[NewItem]]] = defaultdict(
            lambda: defaultdict(list)
        )
        subjects: dict[str, NewSubject] = {}
        latest: dict[str, datetime] = {}
        for e, p in events:
            kind = EVENT_KIND[e.kind]
            if kind not in wanted:
                continue
            watch_id = watches.get(e.program_id)
            day = _day_of(e.created_at, out.zone)
            if kind == NewKind.PROGRAM.value:
                gid = f"library:programs:{day}"
                subjects[gid] = NewSubject(
                    kind=SubjectKind.LIBRARY.value, label="Programs"
                )
                item = self._program_item(e, p, watch_id)
            else:
                gid = f"program:{e.program_id}:{day}"
                subjects[gid] = self._program_subject(e, watch_id)
                scope = scopes.get((e.program_id, e.asset_identifier or ""))
                item = (
                    self._terms_item(e, p, watch_id)
                    if kind in TERMS_KINDS
                    else self._scope_item(e, p, scope, existing, scanned, watch_id)
                )
            by_group[gid][kind].append(item)
            latest[gid] = max(latest.get(gid, e.created_at), e.created_at)

        for gid, sections in by_group.items():
            g = out.group(gid, subjects[gid], latest[gid])
            for kind, items in sections.items():
                if kind == NewKind.SCOPE.value:
                    out.fact(
                        kind,
                        Fact.NOT_TARGET.value,
                        sum(1 for i in items if i.importable and not i.target_exists),
                    )
                out.section(g, kind, len(items), items[:BOUNTY_ROWS_PER_SECTION])

    @staticmethod
    def _program_item(e: BountyEventRow, p: BountyProgram, watch_id) -> NewItem:
        kind = EVENT_KIND[e.kind]
        spec = event_spec(e.kind)
        return NewItem(
            id=f"{kind}:{e.id}",
            kind=kind,
            at=e.created_at,
            value=e.program_name,
            detail=" · ".join(
                x
                for x in (
                    spec.label,
                    "Bounty" if p.offers_bounties else "VDP",
                    e.detail,
                )
                if x
            ),
            tone=NewTone.NEW.value,
            source=p.source,
            source_label=_source_label(p.source),
            platform=e.platform,
            handle=e.handle,
            program_name=e.program_name,
            program_url=p.url,
            watch_id=watch_id,
            importable=p.scopes_synced_at is not None,
        )

    @staticmethod
    def _terms_item(e: BountyEventRow, p: BountyProgram, watch_id) -> NewItem:
        kind = EVENT_KIND[e.kind]
        spec = event_spec(e.kind)
        return NewItem(
            id=f"{kind}:{e.id}",
            kind=kind,
            at=e.created_at,
            value=e.asset_identifier or spec.label,
            detail=e.detail,
            asset_type=ASSET_TYPES_BY_KEY.get(
                (e.asset_type or "").upper(), UNKNOWN_ASSET_TYPE
            ).label
            if e.asset_type
            else None,
            source=p.source,
            source_label=_source_label(p.source),
            platform=e.platform,
            handle=e.handle,
            program_name=e.program_name,
            program_url=p.url,
            watch_id=watch_id,
        )

    @staticmethod
    def _scope_item(
        e: BountyEventRow, p: BountyProgram, scope, existing, scanned, watch_id
    ) -> NewItem:
        kind = EVENT_KIND[e.kind]
        spec = event_spec(e.kind)
        value = scope.target_value if scope else None
        tid = existing.get(value) if value else None
        gone = kind == NewKind.OUT_OF_SCOPE.value
        return NewItem(
            id=f"{kind}:{e.id}",
            kind=kind,
            at=e.created_at,
            value=e.asset_identifier or e.program_name,
            detail=spec.label if gone else _eligibility(scope),
            tone=NewTone.HOT.value if gone else NewTone.NEW.value,
            asset_type=ASSET_TYPES_BY_KEY.get(
                (e.asset_type or "").upper(), UNKNOWN_ASSET_TYPE
            ).label,
            source=p.source,
            source_label=_source_label(p.source),
            platform=e.platform,
            handle=e.handle,
            program_name=e.program_name,
            program_url=p.url,
            watch_id=watch_id,
            scope_id=scope.id if scope else None,
            importable=bool(
                scope and value and scope.scope_state == ScopeState.IN_SCOPE.value
            ),
            target_exists=tid is not None if value else None,
            target_id=tid,
            target_value=value,
            scanned=(tid in scanned) if tid else None,
        )

    async def _scope_rows(self, program_ids: set[UUID], values: set[str]):
        if not program_ids or not values:
            return {}
        rows = (
            await self.session.execute(
                select(BountyScope).where(
                    BountyScope.program_id.in_(program_ids),
                    BountyScope.asset_identifier.in_(values),
                )
            )
        ).scalars()
        return {(s.program_id, s.asset_identifier): s for s in rows}

    async def _existing_targets(self, project_id: UUID, values: set[str]):
        if not values:
            return {}
        rows = await self.session.execute(
            select(Target.target_value, Target.id).where(
                Target.project_id == project_id, Target.target_value.in_(values)
            )
        )
        return dict(rows.all())

    async def _scanned_targets(self, target_ids: set[UUID]) -> set[UUID]:
        if not target_ids:
            return set()
        rows = await self.session.execute(
            select(Scan.target_id)
            .where(Scan.target_id.in_(target_ids), census_only())
            .distinct()
        )
        return {r[0] for r in rows.all()}

    async def _hosts(
        self,
        out: _Groups,
        project_id: UUID,
        since: datetime,
        until: datetime | None,
        grid_start: datetime | None,
        target_ids,
        program,
        wanted: set[str],
        q: str | None,
    ) -> None:
        kind = NewKind.CERT_HOST.value
        base = [
            WatchHost.project_id == project_id,
            WatchHost.state.in_([*ARRIVED_STATES, WatchHostState.MUTED.value]),
        ]
        if target_ids is not None:
            base.append(WatchHost.target_id.in_(target_ids))
        if program is not None:
            base.append(ProgramWatch.program_id == program.id)
        if q:
            base.append(_text_match((WatchHost.name, WatchHost.title), q))
        join = (ProgramWatch, ProgramWatch.id == WatchHost.watch_id)

        if grid_start is not None:
            daily = await self.session.execute(
                select(_local_date(WatchHost.first_seen_at, out.zone), func.count())
                .select_from(WatchHost)
                .join(*join)
                .where(*base, WatchHost.first_seen_at >= grid_start)
                .group_by(_local_date(WatchHost.first_seen_at, out.zone))
            )
            for d, n in daily.all():
                out.day(kind, d, n)

        window = [*base, WatchHost.first_seen_at >= since]
        if until is not None:
            window.append(WatchHost.first_seen_at < until)
        total, answering = (
            await self.session.execute(
                select(
                    func.count(),
                    func.count().filter(WatchHost.status_code.is_not(None)),
                )
                .select_from(WatchHost)
                .join(*join)
                .where(*window)
            )
        ).one()
        out.count(kind, int(total))
        out.fact(kind, Fact.ANSWERING.value, int(answering))
        if kind not in wanted or not total:
            return

        stmt = (
            select(WatchHost, ProgramWatch, BountyProgram, Target)
            .join(*join)
            .join(BountyProgram, BountyProgram.id == ProgramWatch.program_id)
            .join(Target, Target.id == WatchHost.target_id)
            .where(*window)
            .order_by(WatchHost.first_seen_at.desc(), WatchHost.name)
        )
        by_program: dict[str, list[NewItem]] = defaultdict(list)
        subjects: dict[str, NewSubject] = {}
        latest: dict[str, datetime] = {}
        for h, w, p, t in (await self.session.execute(stmt)).all():
            gid = f"program:{p.id}:{_day_of(h.first_seen_at, out.zone)}"
            subjects[gid] = NewSubject(
                kind=SubjectKind.PROGRAM.value,
                id=str(p.id),
                label=p.name,
                platform=p.platform,
                handle=p.handle,
                watched=True,
                watch_id=w.id,
            )
            latest[gid] = max(latest.get(gid, h.first_seen_at), h.first_seen_at)
            by_program[gid].append(
                NewItem(
                    id=f"{kind}:{h.id}",
                    kind=kind,
                    at=h.first_seen_at,
                    value=h.name,
                    detail=h.issuer,
                    status=h.status_code,
                    title=h.title,
                    tech=list(h.tech or [])[:4],
                    ips=list(h.resolved_ips or [])[:2],
                    source=CT_SOURCE,
                    source_label=_source_label(CT_SOURCE),
                    screenshot_path=h.screenshot_path,
                    query=f"host={h.name}",
                    target_id=t.id,
                    target_value=t.target_value,
                    target_type=t.target_type.value,
                    scan_id=h.scan_id,
                    watch_id=w.id,
                    host_id=h.id,
                    platform=p.platform,
                    handle=p.handle,
                    program_name=p.name,
                    program_url=p.url,
                    muted=h.state == WatchHostState.MUTED.value,
                )
            )
        for gid, items in by_program.items():
            g = out.group(gid, subjects[gid], latest[gid])
            out.section(g, kind, len(items), items[:BOUNTY_ROWS_PER_SECTION])

    async def _targets(
        self,
        out: _Groups,
        project_id: UUID,
        since: datetime,
        until: datetime | None,
        grid_start: datetime | None,
        target_ids,
        wanted: set[str],
        q: str | None,
    ) -> None:
        kind = NewKind.TARGET.value
        base = [
            Target.project_id == project_id,
            or_(
                Target.id.in_(self._watch_targets(project_id)),
                Target.id.in_(self._scope_targets(project_id)),
            ),
        ]
        if target_ids is not None:
            base.append(Target.id.in_(target_ids))
        if q:
            base.append(Target.target_value.ilike(f"%{q}%"))

        if grid_start is not None:
            daily = await self.session.execute(
                select(_local_date(Target.created_at, out.zone), func.count())
                .where(*base, Target.created_at >= grid_start)
                .group_by(_local_date(Target.created_at, out.zone))
            )
            for d, n in daily.all():
                out.day(kind, d, n)

        window = [*base, Target.created_at >= since]
        if until is not None:
            window.append(Target.created_at < until)
        targets = (
            (
                await self.session.execute(
                    select(Target)
                    .where(*window)
                    .order_by(Target.created_at.desc(), Target.target_value)
                )
            )
            .scalars()
            .all()
        )
        if not targets:
            return
        scanned = await self._scanned_targets({t.id for t in targets})
        out.count(kind, len(targets))
        out.fact(
            kind, Fact.NOT_SCANNED.value, sum(1 for t in targets if t.id not in scanned)
        )
        if kind not in wanted:
            return
        watched = {
            r[0]
            for r in (
                await self.session.execute(
                    self._watch_targets(project_id).where(
                        TargetOrganization.target_id.in_([t.id for t in targets])
                    )
                )
            ).all()
        }
        names = (
            await self.session.execute(
                select(
                    BountyScope.target_value,
                    BountyProgram.name,
                    BountyProgram.platform,
                    BountyProgram.handle,
                )
                .join(BountyProgram, BountyProgram.id == BountyScope.program_id)
                .where(BountyScope.target_value.in_([t.target_value for t in targets]))
            )
        ).all()
        program_of = {v: (n, pl, h) for v, n, pl, h in names}
        items = []
        for t in targets:
            source = WATCH_SOURCE if t.id in watched else SCOPE_SOURCE
            name, platform, handle = program_of.get(t.target_value, (None, None, None))
            items.append(
                NewItem(
                    id=f"{kind}:{t.id}",
                    kind=kind,
                    at=t.created_at,
                    value=t.target_value,
                    detail=name,
                    source=source,
                    source_label=_source_label(source),
                    target_id=t.id,
                    target_value=t.target_value,
                    target_type=t.target_type.value,
                    platform=platform,
                    handle=handle,
                    program_name=name,
                    scanned=t.id in scanned,
                )
            )
        by_day: dict[str, list[NewItem]] = defaultdict(list)
        for item in items:
            by_day[_day_of(item.at, out.zone)].append(item)
        for day, listed in by_day.items():
            g = out.group(
                f"targets:{day}",
                NewSubject(kind=SubjectKind.TARGETS.value, label="Targets"),
                listed[0].at,
            )
            out.section(g, kind, len(listed), listed[:BOUNTY_ROWS_PER_SECTION])
