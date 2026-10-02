from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import JSONB, array
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.scan import scan_duration
from app.services.surface_scope import SurfaceScopeService
from app.services.target_scope import Targets
from app.services.threat_intel import ThreatIntelService
from app.services.watch import WatchService
from shared.definitions.bounty_programs import event_spec
from shared.definitions.connectors import LOUD_NOTICES, NoticeKind
from shared.definitions.dashboard import (
    ACTIVITY_LIMIT,
    SERIES_DAYS,
    WINDOW_DAYS,
    ActivityKind,
    ActivityTone,
    window_key,
    window_since,
)
from shared.definitions.surface import SurfaceDimension
from shared.definitions.threat_intel import FEEDS_BY_KIND, SIGNALS_BY_KIND
from shared.definitions.watch import (
    EVENT_LABELS,
    HOST_STATE_LABELS,
    WatchEventKind,
    WatchHostState,
)
from shared.enums.scan import ScanStatus
from shared.models.bounty_program import BountyEventRow, BountyProgram
from shared.models.connector import Connector, ConnectorCandidate
from shared.models.dashboard import (
    DashboardActivity,
    DashboardBrowsing,
    DashboardDayKinds,
    DashboardEvent,
    DashboardLadderStep,
    DashboardPrograms,
    DashboardWatchAlert,
    DashboardWatches,
)
from shared.models.scan import Scan
from shared.models.target import Target
from shared.models.threat_intel import ThreatFeed
from shared.models.watch import ProgramWatch, WatchEvent, WatchHost
from shared.services.scan_scope import census_only
from shared.utils.datetime import duration_text, utc_now
from shared.utils.text import plural

_HOT_STATUSES = (ScanStatus.FAILED.value, ScanStatus.CANCELLED.value)
_WATCH_KINDS = (
    WatchEventKind.HOST_ALERTED.value,
    WatchEventKind.SCOPE_ADDED.value,
    WatchEventKind.SCOPE_REMOVED.value,
    WatchEventKind.STREAM_ERROR.value,
)
INTEL_EVENTS = 5
LADDER = (
    WatchHostState.NEW,
    WatchHostState.UNRESOLVED,
    WatchHostState.KNOWN,
    WatchHostState.PROBING,
    WatchHostState.QUIET,
    WatchHostState.ALERTED,
)
_STATUS_LABEL = {
    ScanStatus.COMPLETED.value: "run completed",
    ScanStatus.FAILED.value: "run failed",
    ScanStatus.CANCELLED.value: "run cancelled",
}


def _window(window: str) -> tuple[str, datetime]:
    window = window_key(window)
    return window, window_since(window, utc_now())


def _days(now: datetime, span: int) -> list[str]:
    start = now.date() - timedelta(days=span)
    return [(start + timedelta(days=i)).isoformat() for i in range(span + 1)]


class DashboardActivityService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def activity(
        self,
        project_id: UUID,
        window: str,
        *,
        programs: bool,
        targets: Targets = None,
    ) -> DashboardActivity:
        window, cutoff = _window(window)
        events: list[DashboardEvent] = []
        events += await self._runs(project_id, cutoff, targets)
        events += await self._intel(project_id, window, targets)
        if targets is None:
            events += await self._feeds(cutoff)
            events += await self._connectors(project_id, cutoff)
        if programs and targets is None:
            events += await self._watch_events(project_id, cutoff)
            events += await self._bounty_events(cutoff)
        events.sort(key=lambda e: e.at, reverse=True)
        return DashboardActivity(window=window, events=events[:ACTIVITY_LIMIT])

    async def _runs(
        self, project_id: UUID, cutoff: datetime, targets: Targets = None
    ) -> list[DashboardEvent]:
        scoped = [] if targets is None else [Scan.target_id.in_(targets)]
        rows = await self.session.execute(
            select(Scan, Target.target_value)
            .join(Target, Target.id == Scan.target_id)
            .where(
                *scoped,
                Scan.project_id == project_id,
                census_only(),
                Scan.completed_at.isnot(None),
                Scan.completed_at >= cutoff,
                Scan.status.in_(tuple(_STATUS_LABEL)),
            )
            .order_by(Scan.completed_at.desc())
            .limit(ACTIVITY_LIMIT)
        )
        out = []
        for scan, target_value in rows.all():
            parts: list[str] = []
            if scan.status == ScanStatus.COMPLETED.value:
                found = scan.vulnerabilities_found
                hosts = scan.subdomains_found
                parts.append(f"{found:,} {plural(found, 'finding')}")
                parts.append(f"{hosts:,} {plural(hosts, 'web asset')}")
            elif scan.error:
                parts.append(scan.error[:140])
            if ran := scan_duration(scan):
                parts.append(duration_text(ran))
            out.append(
                DashboardEvent(
                    at=scan.completed_at,
                    kind=ActivityKind.RUN.value,
                    label="Run",
                    title=f"{target_value} {_STATUS_LABEL[scan.status]}",
                    detail=" · ".join(parts) or None,
                    tone=ActivityTone.HOT.value
                    if scan.status in _HOT_STATUSES
                    else ActivityTone.NEUTRAL.value,
                    scan_id=scan.id,
                )
            )
        return out

    async def _feeds(self, cutoff: datetime) -> list[DashboardEvent]:
        rows = await self.session.execute(
            select(ThreatFeed).where(
                ThreatFeed.kind.in_(list(FEEDS_BY_KIND)),
                ThreatFeed.last_synced_at.isnot(None),
                ThreatFeed.last_synced_at >= cutoff,
            )
        )
        out = []
        for feed in rows.scalars().all():
            spec = FEEDS_BY_KIND.get(feed.kind)
            label = spec.label if spec else feed.kind
            out.append(
                DashboardEvent(
                    at=feed.last_synced_at,
                    kind=ActivityKind.FEEDS.value,
                    label="Feeds",
                    title=f"{label} refreshed",
                    detail=(
                        f"{feed.rows:,} {plural(feed.rows, 'row')}"
                        if feed.rows
                        else None
                    ),
                )
            )
        return out

    async def _intel(
        self, project_id: UUID, window: str, targets: Targets = None
    ) -> list[DashboardEvent]:
        scope = await SurfaceScopeService(self.session).scope(
            project_id, SurfaceDimension.VULNERABILITIES.value, targets=targets
        )
        changes = await ThreatIntelService(self.session).changes(
            scope, days=WINDOW_DAYS[window], limit=ACTIVITY_LIMIT * 4
        )
        grouped: dict[tuple, list] = defaultdict(list)
        for c in changes:
            if c.changed_at is None:
                continue
            key = (c.template_name, c.change, c.target_id, c.changed_at.date())
            grouped[key].append(c)
        out = []
        for (template, change, _target, _day), items in sorted(
            grouped.items(),
            key=lambda kv: max(c.changed_at for c in kv[1]),
            reverse=True,
        )[:INTEL_EVENTS]:
            first = max(items, key=lambda c: c.changed_at)
            hosts = len({c.host or c.matched_at for c in items})
            parts = [p for p in (first.cve, first.target_value) if p]
            if hosts > 1:
                parts.append(f"on {hosts} web assets")
            spec = SIGNALS_BY_KIND.get(change)
            out.append(
                DashboardEvent(
                    at=first.changed_at,
                    kind=ActivityKind.INTEL.value,
                    label="Exploitation",
                    title=f"{template} · {spec.label if spec else change}",
                    detail=" · ".join(parts) or None,
                    tone=ActivityTone.HOT.value,
                    scan_id=first.scan_id,
                )
            )
        return out

    async def _connectors(
        self, project_id: UUID, cutoff: datetime
    ) -> list[DashboardEvent]:
        rows = await self.session.execute(
            select(Connector).where(
                Connector.project_id == project_id,
                Connector.last_seen_at.isnot(None),
                Connector.last_seen_at >= cutoff,
            )
        )
        connectors = rows.scalars().all()
        if not connectors:
            return []
        notices = cast(ConnectorCandidate.notices, JSONB)
        unseen = dict(
            (
                await self.session.execute(
                    select(ConnectorCandidate.connector_id, func.count())
                    .where(
                        ConnectorCandidate.connector_id.in_([c.id for c in connectors]),
                        notices.contains([NoticeKind.UNSEEN_BY_SCANS.value]),
                    )
                    .group_by(ConnectorCandidate.connector_id)
                )
            ).all()
        )
        return [
            DashboardEvent(
                at=c.last_seen_at,
                kind=ActivityKind.CONNECTOR.value,
                label="Connector",
                title=f"{c.name} synced",
                detail=(
                    f"{n:,} {plural(n, 'browsed endpoint')} unseen by scans"
                    if (n := unseen.get(c.id, 0))
                    else f"{c.requests_seen:,} {plural(c.requests_seen, 'request')}"
                ),
            )
            for c in connectors
        ]

    async def _watch_events(
        self, project_id: UUID, cutoff: datetime
    ) -> list[DashboardEvent]:
        rows = await self.session.execute(
            select(
                WatchEvent,
                BountyProgram.name,
                BountyProgram.platform,
                BountyProgram.handle,
            )
            .join(ProgramWatch, ProgramWatch.id == WatchEvent.watch_id)
            .join(BountyProgram, BountyProgram.id == ProgramWatch.program_id)
            .where(
                WatchEvent.project_id == project_id,
                WatchEvent.created_at >= cutoff,
                WatchEvent.kind.in_(_WATCH_KINDS),
            )
            .order_by(WatchEvent.created_at.desc())
            .limit(ACTIVITY_LIMIT)
        )
        out = []
        for event, program_name, platform, handle in rows.all():
            hot = event.kind == WatchEventKind.STREAM_ERROR.value
            fresh = event.kind == WatchEventKind.HOST_ALERTED.value
            out.append(
                DashboardEvent(
                    at=event.created_at,
                    kind=ActivityKind.WATCH.value,
                    label="Watch",
                    title=f"{program_name} · {EVENT_LABELS.get(event.kind, event.kind)}",
                    detail=event.name or event.detail,
                    tone=ActivityTone.HOT.value
                    if hot
                    else ActivityTone.NEW.value
                    if fresh
                    else ActivityTone.NEUTRAL.value,
                    watch_id=event.watch_id,
                    platform=platform,
                    handle=handle,
                )
            )
        return out

    async def _bounty_events(self, cutoff: datetime) -> list[DashboardEvent]:
        rows = await self.session.execute(
            select(BountyEventRow)
            .where(BountyEventRow.created_at >= cutoff)
            .order_by(BountyEventRow.created_at.desc())
            .limit(ACTIVITY_LIMIT)
        )
        out = []
        for row in rows.scalars().all():
            spec = event_spec(row.kind)
            out.append(
                DashboardEvent(
                    at=row.created_at,
                    kind=ActivityKind.PROGRAM.value,
                    label="Program",
                    title=f"{row.program_name} · {spec.label}",
                    detail=row.asset_identifier or row.detail,
                    tone=ActivityTone.NEW.value
                    if spec.actionable
                    else ActivityTone.NEUTRAL.value,
                    platform=row.platform,
                    handle=row.handle,
                )
            )
        return out

    async def programs(self, project_id: UUID, window: str) -> DashboardPrograms:
        window = window_key(window)
        now = utc_now()
        since = window_since(window, now)
        days = _days(now, SERIES_DAYS)
        series_cutoff = datetime.combine(
            date.fromisoformat(days[0]), time.min, tzinfo=UTC
        )
        out = DashboardPrograms(window=window, since=since)

        by_platform = await self.session.execute(
            select(BountyProgram.platform, func.count()).group_by(
                BountyProgram.platform
            )
        )
        out.by_platform = {str(p): int(n) for p, n in by_platform.all()}
        out.programs_total = sum(out.by_platform.values())

        per_day: dict[str, DashboardDayKinds] = {
            d: DashboardDayKinds(date=d) for d in days
        }
        rows = await self.session.execute(
            select(
                func.date(BountyEventRow.created_at),
                BountyEventRow.kind,
                func.count(),
            )
            .where(BountyEventRow.created_at >= series_cutoff)
            .group_by(func.date(BountyEventRow.created_at), BountyEventRow.kind)
        )
        for day, kind, n in rows.all():
            key = day.isoformat()
            if key in per_day:
                per_day[key].kinds[kind] = int(n)
        out.events_daily = list(per_day.values())
        in_window = await self.session.execute(
            select(BountyEventRow.kind, func.count())
            .where(BountyEventRow.created_at >= since)
            .group_by(BountyEventRow.kind)
        )
        out.events_in_window = {kind: int(n) for kind, n in in_window.all()}

        out.watches = await self._watches(project_id, days, series_cutoff)
        out.browsing = await self._browsing(project_id, days, series_cutoff)
        return out

    async def _watches(
        self, project_id: UUID, days: list[str], series_cutoff: datetime
    ) -> DashboardWatches:
        out = DashboardWatches()
        out.total = int(
            await self.session.scalar(
                select(func.count()).where(ProgramWatch.project_id == project_id)
            )
            or 0
        )
        if not out.total:
            return out
        in_project = ProgramWatch.project_id == project_id
        ladder = await self.session.execute(
            select(WatchHost.state, func.count())
            .join(ProgramWatch, ProgramWatch.id == WatchHost.watch_id)
            .where(in_project)
            .group_by(WatchHost.state)
        )
        by_state = {str(state): int(n) for state, n in ladder.all()}
        out.ladder = [
            DashboardLadderStep(
                state=state.value,
                label=HOST_STATE_LABELS.get(state.value, state.value),
                count=by_state.get(state.value, 0),
            )
            for state in LADDER
        ]
        per_day = {d: DashboardDayKinds(date=d) for d in days}
        seen = await self.session.execute(
            select(func.date(WatchHost.first_seen_at), func.count())
            .join(ProgramWatch, ProgramWatch.id == WatchHost.watch_id)
            .where(in_project, WatchHost.first_seen_at >= series_cutoff)
            .group_by(func.date(WatchHost.first_seen_at))
        )
        for day, n in seen.all():
            key = day.isoformat()
            if key in per_day:
                per_day[key].kinds["seen"] = int(n)
        alerted = await self.session.execute(
            select(func.date(WatchHost.alerted_at), func.count())
            .join(ProgramWatch, ProgramWatch.id == WatchHost.watch_id)
            .where(
                in_project,
                WatchHost.alerted_at.isnot(None),
                WatchHost.alerted_at >= series_cutoff,
            )
            .group_by(func.date(WatchHost.alerted_at))
        )
        for day, n in alerted.all():
            key = day.isoformat()
            if key in per_day:
                per_day[key].kinds["alerted"] = int(n)
        out.daily = list(per_day.values())
        latest = (
            await self.session.execute(
                select(WatchHost, BountyProgram.name)
                .join(ProgramWatch, ProgramWatch.id == WatchHost.watch_id)
                .join(BountyProgram, BountyProgram.id == ProgramWatch.program_id)
                .where(
                    in_project,
                    WatchHost.state == WatchHostState.ALERTED.value,
                    WatchHost.alerted_at.isnot(None),
                )
                .order_by(WatchHost.alerted_at.desc())
                .limit(1)
            )
        ).first()
        if latest:
            host, program_name = latest
            out.latest_alert = DashboardWatchAlert(
                watch_id=host.watch_id,
                name=host.name,
                program_name=program_name,
                at=host.alerted_at,
            )
        stream = await WatchService.stream_status()
        out.stream_running = bool(stream.running and stream.reachable)
        out.stream_certificates = int(stream.certificates_seen or 0)
        out.last_certificate_at = stream.last_certificate_at
        return out

    async def _browsing(
        self, project_id: UUID, days: list[str], series_cutoff: datetime
    ) -> DashboardBrowsing:
        out = DashboardBrowsing()
        connectors = (
            (
                await self.session.execute(
                    select(Connector).where(Connector.project_id == project_id)
                )
            )
            .scalars()
            .all()
        )
        out.connectors = len(connectors)
        if not connectors:
            return out
        out.last_seen_at = max(
            (c.last_seen_at for c in connectors if c.last_seen_at), default=None
        )
        notices = cast(ConnectorCandidate.notices, JSONB)
        scope = ConnectorCandidate.project_id == project_id
        counted = (
            await self.session.execute(
                select(
                    func.count(),
                    func.count().filter(
                        notices.contains([NoticeKind.UNSEEN_BY_SCANS.value])
                    ),
                    func.count().filter(
                        notices.contains([NoticeKind.NEW_PARAMS.value])
                    ),
                    func.count().filter(notices.has_any(array(tuple(LOUD_NOTICES)))),
                ).where(scope)
            )
        ).one()
        out.browsed, out.unseen, out.new_params, out.flagged = (
            int(v or 0) for v in counted
        )
        per_day = {d: DashboardDayKinds(date=d) for d in days}
        rows = await self.session.execute(
            select(func.date(ConnectorCandidate.first_seen_at), func.count())
            .where(scope, ConnectorCandidate.first_seen_at >= series_cutoff)
            .group_by(func.date(ConnectorCandidate.first_seen_at))
        )
        for day, n in rows.all():
            key = day.isoformat()
            if key in per_day:
                per_day[key].kinds["browsed"] = int(n)
        out.daily = list(per_day.values())
        return out
