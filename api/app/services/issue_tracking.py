"""Issue trackers, their project routes, and filing findings into issues."""

from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import exists, func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from app.services.target_names import target_names
from shared.definitions.issue_trackers import (
    MAX_ERROR,
    MAX_FILE_SELECTION,
    MAX_LISTED,
    MAX_TRACKERS,
    SHEET_REFRESH_SECONDS,
    TRACKERS_BY_KIND,
    FilingState,
    RemoteCategory,
    TrackerSpec,
    secret_fields,
    valid_destination,
)
from shared.definitions.vulnerabilities import SUPPRESSED_STATES
from shared.models.issue_tracker import (
    FileSelection,
    FilingPlan,
    FilingResult,
    IssueTracker,
    IssueTrackerCreate,
    IssueTrackerRead,
    IssueTrackerRoute,
    IssueTrackerTestConfig,
    IssueTrackerTestResult,
    IssueTrackerUpdate,
    PlannedIssue,
    PreviewBlock,
    RouteRead,
    RouteSet,
    TicketRef,
    TrackedIssue,
    TrackedIssueFinding,
    TrackedIssueRead,
    TrackerOption,
)
from shared.models.project import Project
from shared.models.target import Target
from shared.models.vulnerability import Vulnerability, VulnerabilityTriage
from shared.services import locks
from shared.services.asset_query import QueryScope, ScopeLike, lead_cache
from shared.services.celery_dispatch import dispatch_issue_filing
from shared.services.issue_trackers import (
    Tracker,
    TrackerError,
    client_for,
    open_config,
    seal_config,
    tracker_client,
)
from shared.services.issue_tracking import body as bodies
from shared.services.issue_tracking.plan import OpenIssue, Plan, plan_filing
from shared.services.issue_tracking.sync import NOT_FOUND
from shared.services.scan_resolve import MASK
from shared.utils.datetime import utc_now
from shared.utils.net import validate_public_https_url

_TAIL = 4
_OPEN_STATES = (FilingState.PENDING.value, FilingState.FILED.value)


def _bad(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


_TRACKER_MISSING = "Issue tracker not found"
_ROUTE_MISSING = "Route not found"
_ISSUE_MISSING = "Issue not found"
_PROJECT_MISSING = "Project not found"
_TARGET_MISSING = "Target not found"
_NOT_RETRYABLE = "Retry applies to issues that were not filed."


def _missing(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _spec(kind: str) -> TrackerSpec:
    spec = TRACKERS_BY_KIND.get(kind)
    if spec is None:
        msg = f"Unknown tracker type {kind}."
        raise _bad(msg)
    return spec


# ---------- config ----------


def _mask(kind: str, config: dict) -> dict:
    hidden = secret_fields(kind)
    out: dict = {}
    for key, value in config.items():
        if key in hidden and isinstance(value, str):
            out[key] = f"{MASK}{value[-_TAIL:]}" if len(value) > _TAIL * 2 else MASK
        else:
            out[key] = value
    return out


def _merge(kind: str, stored: dict, incoming: dict) -> dict:
    merged = {k: v for k, v in incoming.items() if v is not None}
    for key in secret_fields(kind):
        value = incoming.get(key)
        if value in (None, ""):
            if key in stored:
                merged[key] = stored[key]
            else:
                merged.pop(key, None)
        elif isinstance(value, str) and MASK in value and key in stored:
            merged[key] = stored[key]
    return merged


def _clean_config(spec: TrackerSpec, config: dict) -> dict:
    out: dict = {}
    for field in spec.fields:
        value = config.get(field.key)
        if not isinstance(value, str) or not value.strip():
            msg = f"{field.label} is required."
            raise _bad(msg)
        if MASK in value:
            msg = f"{field.label} carries a masked value. Enter it again."
            raise _bad(msg)
        out[field.key] = value.strip()
    return out


async def _clean_url(spec: TrackerSpec, url: str | None) -> str:
    value = (url or spec.default_url or "").strip().rstrip("/")
    if not value:
        msg = f"{spec.url_label} is required."
        raise _bad(msg)
    try:
        await asyncio.to_thread(validate_public_https_url, value, label=spec.url_label)
    except ValueError as exc:
        raise _bad(str(exc)) from None
    return value


def _clean_destination(kind: str, value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    value = value.strip()
    if not valid_destination(kind, value):
        spec = _spec(kind)
        msg = (
            f"{spec.destination_label} {value} is not valid. "
            f"Format: {spec.destination_placeholder}."
        )
        raise _bad(msg)
    return value


def _scrub(message: str, config: dict, kind: str) -> str:
    for key in secret_fields(kind):
        value = config.get(key)
        if isinstance(value, str) and value:
            message = message.replace(value, MASK)
    return message[:MAX_ERROR]


async def _run(client: Tracker, fn, *args):
    try:
        return await asyncio.to_thread(fn, *args)
    finally:
        client.close()


async def _verify(kind: str, url: str, config: dict) -> IssueTrackerTestResult:
    client = client_for(kind, url, config)
    try:
        account = await _run(client, client.verify)
    except TrackerError as exc:
        return IssueTrackerTestResult(
            success=False, message=_scrub(str(exc), config, kind)
        )
    message = f"Connected as {account}." if account else "Connected."
    return IssueTrackerTestResult(success=True, message=message)


def _tracker_read(
    row: IssueTracker, counts: dict[str, int], *, reveal: bool
) -> IssueTrackerRead:
    return IssueTrackerRead(
        id=row.id,
        name=row.name,
        kind=row.kind,
        url=row.url,
        config_masked=_mask(row.kind, open_config(row)) if reveal else {},
        destination=row.destination,
        issue_type=row.issue_type,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
        last_test_at=row.last_test_at,
        last_test_ok=row.last_test_ok,
        last_test_message=row.last_test_message if reveal else None,
        issues_filed=counts.get(FilingState.FILED.value, 0),
        issues_failed=counts.get(FilingState.FAILED.value, 0),
    )


class IssueTrackerService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _row(self, id: uuid.UUID) -> IssueTracker:
        row = await self.session.get(IssueTracker, id)
        if row is None:
            raise _missing(_TRACKER_MISSING)
        return row

    async def _counts(self) -> dict[uuid.UUID, dict[str, int]]:
        rows = await self.session.execute(
            select(TrackedIssue.tracker_id, TrackedIssue.state, func.count()).group_by(
                TrackedIssue.tracker_id, TrackedIssue.state
            )
        )
        out: dict[uuid.UUID, dict[str, int]] = defaultdict(dict)
        for tracker_id, state, n in rows.all():
            out[tracker_id][state] = int(n)
        return out

    async def list(self, *, reveal: bool) -> list[IssueTrackerRead]:
        rows = (
            (
                await self.session.execute(
                    select(IssueTracker).order_by(IssueTracker.name)
                )
            )
            .scalars()
            .all()
        )
        counts = await self._counts()
        return [_tracker_read(r, counts.get(r.id, {}), reveal=reveal) for r in rows]

    async def get(self, id: uuid.UUID, *, reveal: bool) -> IssueTrackerRead:
        row = await self._row(id)
        counts = await self._counts()
        return _tracker_read(row, counts.get(row.id, {}), reveal=reveal)

    async def create(
        self, data: IssueTrackerCreate, user_id: uuid.UUID
    ) -> IssueTrackerRead:
        spec = _spec(data.kind)
        total = await self.session.scalar(
            select(func.count()).select_from(IssueTracker)
        )
        if int(total or 0) >= MAX_TRACKERS:
            msg = f"Limit of {MAX_TRACKERS} trackers reached."
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)
        config = _clean_config(spec, data.config)
        row = IssueTracker(
            name=data.name,
            kind=spec.kind.value,
            url=await _clean_url(spec, data.url),
            config_encrypted=seal_config(config),
            destination=_clean_destination(data.kind, data.destination),
            issue_type=(data.issue_type or "").strip() or None,
            is_active=data.is_active,
            created_by=user_id,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return _tracker_read(row, {}, reveal=True)

    async def update(self, id: uuid.UUID, data: IssueTrackerUpdate) -> IssueTrackerRead:
        row = await self._row(id)
        spec = _spec(row.kind)
        fields = data.model_fields_set
        if data.name is not None:
            row.name = data.name
        moved = False
        if data.url is not None:
            url = await _clean_url(spec, data.url)
            moved = url != row.url
            row.url = url
        if data.config is not None or moved:
            stored = {} if moved else open_config(row)
            merged = _merge(row.kind, stored, data.config or {})
            row.config_encrypted = seal_config(_clean_config(spec, merged))
            row.last_test_at = row.last_test_ok = row.last_test_message = None
        if "destination" in fields:
            row.destination = _clean_destination(row.kind, data.destination)
        if "issue_type" in fields:
            row.issue_type = (data.issue_type or "").strip() or None
        if data.is_active is not None:
            row.is_active = data.is_active
        row.updated_at = utc_now()
        await self.session.commit()
        return await self.get(row.id, reveal=True)

    async def delete(self, id: uuid.UUID) -> None:
        row = await self._row(id)
        targets = (
            await self.session.execute(
                select(TrackedIssue.target_id)
                .where(TrackedIssue.tracker_id == id)
                .distinct()
            )
        ).scalars()
        touched = set(targets)
        await self.session.delete(row)
        await self.session.commit()
        if touched:
            await lead_cache.bump(touched)

    async def test_config(self, data: IssueTrackerTestConfig) -> IssueTrackerTestResult:
        spec = _spec(data.kind)
        config = data.config
        url = await _clean_url(spec, data.url)
        if data.tracker_id is not None:
            stored = await self._row(data.tracker_id)
            same = stored.kind == spec.kind.value and stored.url == url
            config = _merge(stored.kind, open_config(stored) if same else {}, config)
        return await _verify(spec.kind.value, url, _clean_config(spec, config))

    async def test(self, id: uuid.UUID) -> IssueTrackerTestResult:
        row = await self._row(id)
        result = await _verify(row.kind, row.url, open_config(row))
        row.last_test_at = utc_now()
        row.last_test_ok = result.success
        row.last_test_message = result.message[:MAX_ERROR]
        await self.session.commit()
        return result

    async def _remote(
        self, row: IssueTracker, fn_name: str, *args
    ) -> list[TrackerOption]:
        client = tracker_client(row)
        try:
            options = await _run(client, getattr(client, fn_name), *args)
        except TrackerError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=_scrub(str(exc), open_config(row), row.kind),
            ) from None
        return [TrackerOption(key=o.key, name=o.name) for o in options]

    async def destinations(self, id: uuid.UUID, query: str) -> list[TrackerOption]:
        return await self._remote(await self._row(id), "destinations", query)

    async def issue_types(self, id: uuid.UUID, destination: str) -> list[TrackerOption]:
        row = await self._row(id)
        if _clean_destination(row.kind, destination) is None:
            return []
        return await self._remote(row, "issue_types", destination)

    # ---------- routes ----------

    async def routes(self, project_id: uuid.UUID) -> list[RouteRead]:
        rows = (
            (
                await self.session.execute(
                    select(IssueTrackerRoute).where(
                        IssueTrackerRoute.project_id == project_id
                    )
                )
            )
            .scalars()
            .all()
        )
        names = await target_names(self.session, (r.target_id for r in rows))
        out = [
            RouteRead(
                id=r.id,
                project_id=r.project_id,
                target_id=r.target_id,
                target_value=names.get(r.target_id) if r.target_id else None,
                tracker_id=r.tracker_id,
                destination=r.destination,
                issue_type=r.issue_type,
            )
            for r in rows
        ]
        return sorted(
            out, key=lambda r: (r.target_id is not None, r.target_value or "")
        )

    async def set_route(self, data: RouteSet) -> RouteRead:
        tracker = await self._row(data.tracker_id)
        if await self.session.get(Project, data.project_id) is None:
            raise _missing(_PROJECT_MISSING)
        if data.target_id is not None:
            owner = await self.session.scalar(
                select(Target.project_id).where(Target.id == data.target_id)
            )
            if owner != data.project_id:
                raise _missing(_TARGET_MISSING)
        destination = _clean_destination(tracker.kind, data.destination)
        if destination is None:
            msg = f"{_spec(tracker.kind).destination_label} is required."
            raise _bad(msg)
        stmt = select(IssueTrackerRoute).where(
            IssueTrackerRoute.project_id == data.project_id,
            IssueTrackerRoute.target_id == data.target_id
            if data.target_id
            else IssueTrackerRoute.target_id.is_(None),
        )
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if row is None:
            row = IssueTrackerRoute(
                project_id=data.project_id, target_id=data.target_id
            )
            self.session.add(row)
        row.tracker_id = tracker.id
        row.destination = destination
        row.issue_type = (data.issue_type or "").strip() or None
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Route not saved. A route for this scope exists.",
            ) from None
        names = await target_names(self.session, [row.target_id])
        return RouteRead(
            id=row.id,
            project_id=row.project_id,
            target_id=row.target_id,
            target_value=names.get(row.target_id) if row.target_id else None,
            tracker_id=row.tracker_id,
            destination=row.destination,
            issue_type=row.issue_type,
        )

    async def delete_route(self, id: uuid.UUID) -> None:
        row = await self.session.get(IssueTrackerRoute, id)
        if row is None:
            raise _missing(_ROUTE_MISSING)
        await self.session.delete(row)
        await self.session.commit()


# ---------- tickets on findings ----------


async def ticket_refs(
    session: AsyncSession, pairs: Iterable[tuple[uuid.UUID, str]]
) -> dict[tuple[uuid.UUID, str], list[TicketRef]]:
    wanted = set(pairs)
    if not wanted:
        return {}
    rows = await session.execute(
        select(
            TrackedIssueFinding.target_id,
            TrackedIssueFinding.fingerprint,
            TrackedIssue,
            IssueTracker,
        )
        .join(TrackedIssue, TrackedIssue.id == TrackedIssueFinding.issue_id)
        .join(IssueTracker, IssueTracker.id == TrackedIssue.tracker_id)
        .where(
            TrackedIssueFinding.target_id.in_({t for t, _ in wanted}),
            TrackedIssueFinding.fingerprint.in_({f for _, f in wanted}),
        )
        .order_by(TrackedIssue.created_at)
    )
    out: dict[tuple[uuid.UUID, str], list[TicketRef]] = defaultdict(list)
    for target_id, fingerprint, issue, tracker in rows.all():
        if (target_id, fingerprint) not in wanted:
            continue
        out[(target_id, fingerprint)].append(
            TicketRef(
                issue_id=issue.id,
                tracker_name=tracker.name,
                tracker_kind=tracker.kind,
                state=issue.state,
                external_key=issue.external_key,
                url=issue.url,
                remote_status=issue.remote_status,
                remote_category=issue.remote_category,
                error=issue.error,
            )
        )
    return out


# ---------- filing ----------


@dataclass(frozen=True)
class Destination:
    tracker: IssueTracker
    destination: str
    issue_type: str | None


_NO_ROUTE = "No route for this project. Select a tracker."
_ROUTE_OFF = "Tracker for {scope} is disabled."
_OFF_ROUTE = "{label} {destination} has no route in this project."
_TOO_MANY = "Selection has {n} findings. The limit is {cap}."
_DEFERRED = (Vulnerability.request, Vulnerability.response)


class IssueFilingService:
    def __init__(self, session: AsyncSession, *, admin: bool = False):
        self.session = session
        self.admin = admin

    async def _selection(
        self, scope: ScopeLike, sel: FileSelection
    ) -> list[Vulnerability] | str:
        if not sel.fingerprints and not sel.template_ids:
            return []
        picks = []
        if sel.fingerprints:
            picks.append(Vulnerability.fingerprint.in_(sel.fingerprints))
        if sel.template_ids:
            picks.append(Vulnerability.template_id.in_(sel.template_ids))
        set_aside = exists(
            select(1).where(
                VulnerabilityTriage.target_id == Vulnerability.target_id,
                VulnerabilityTriage.fingerprint == Vulnerability.fingerprint,
                VulnerabilityTriage.state.in_(SUPPRESSED_STATES),
            )
        )
        rows = (
            await self.session.execute(
                select(Vulnerability)
                .options(*(defer(column) for column in _DEFERRED))
                .where(
                    QueryScope.of(scope).match(Vulnerability.scan_id),
                    or_(*picks),
                    ~set_aside,
                )
                .order_by(Vulnerability.discovered_at.desc())
            )
        ).scalars()
        latest: dict[tuple[uuid.UUID, str], Vulnerability] = {}
        for row in rows:
            latest.setdefault((row.target_id, row.fingerprint), row)
        if len(latest) > MAX_FILE_SELECTION:
            return _TOO_MANY.format(n=len(latest), cap=MAX_FILE_SELECTION)
        return list(latest.values())

    async def _destinations(
        self, vulns: list[Vulnerability], sel: FileSelection
    ) -> dict[uuid.UUID, Destination] | str:
        targets = {v.target_id for v in vulns}
        projects = {v.project_id for v in vulns}
        trackers = {
            t.id: t
            for t in (await self.session.execute(select(IssueTracker))).scalars()
        }
        active = {k: t for k, t in trackers.items() if t.is_active}
        routes = list(
            (
                await self.session.execute(
                    select(IssueTrackerRoute).where(
                        IssueTrackerRoute.project_id.in_(projects)
                    )
                )
            ).scalars()
        )
        if sel.tracker_id is not None:
            return self._chosen(sel, active, routes, targets)
        by_target = {r.target_id: r for r in routes if r.target_id is not None}
        by_project = {r.project_id: r for r in routes if r.target_id is None}
        fallback = [t for t in active.values() if t.destination]
        project_of = {v.target_id: v.project_id for v in vulns}
        names = await target_names(self.session, targets)
        out: dict[uuid.UUID, Destination] = {}
        for target_id in targets:
            route = by_target.get(target_id) or by_project.get(project_of[target_id])
            if route is not None:
                if route.tracker_id not in active:
                    return _ROUTE_OFF.format(scope=names.get(target_id, "this target"))
                out[target_id] = Destination(
                    active[route.tracker_id], route.destination, route.issue_type
                )
            elif len(fallback) == 1:
                only = fallback[0]
                out[target_id] = Destination(
                    only, only.destination or "", only.issue_type
                )
            else:
                return _NO_ROUTE
        return out

    def _chosen(
        self,
        sel: FileSelection,
        active: dict[uuid.UUID, IssueTracker],
        routes: list[IssueTrackerRoute],
        targets: set[uuid.UUID],
    ) -> dict[uuid.UUID, Destination] | str:
        tracker = active.get(sel.tracker_id) if sel.tracker_id else None
        if tracker is None:
            return "Tracker is disabled or removed."
        own = [r for r in routes if r.tracker_id == tracker.id]
        allowed = {r.destination: r.issue_type for r in own}
        if tracker.destination:
            allowed.setdefault(tracker.destination, tracker.issue_type)
        destination = _clean_destination(tracker.kind, sel.destination)
        if destination is None:
            destination = tracker.destination or (own[0].destination if own else None)
        if destination is None:
            return f"Select a {_spec(tracker.kind).destination_label.lower()}."
        if not self.admin and destination not in allowed:
            return _OFF_ROUTE.format(
                label=_spec(tracker.kind).destination_label, destination=destination
            )
        issue_type = (sel.issue_type if self.admin else None) or allowed.get(
            destination
        )
        return dict.fromkeys(targets, Destination(tracker, destination, issue_type))

    async def _plan(
        self, scope: ScopeLike, sel: FileSelection
    ) -> tuple[list[tuple[Destination, Plan, int]], str | None, dict[uuid.UUID, str]]:
        vulns = await self._selection(scope, sel)
        if isinstance(vulns, str):
            return [], vulns, {}
        if not vulns:
            return [], None, {}
        resolved = await self._destinations(vulns, sel)
        if isinstance(resolved, str):
            return [], resolved, {}
        groups: dict[tuple[uuid.UUID, str, str | None], list[Vulnerability]] = (
            defaultdict(list)
        )
        where: dict[tuple[uuid.UUID, str, str | None], Destination] = {}
        for vuln in vulns:
            dest = resolved[vuln.target_id]
            key = (dest.tracker.id, dest.destination, dest.issue_type)
            groups[key].append(vuln)
            where[key] = dest
        out: list[tuple[Destination, Plan, int]] = []
        for key, members in groups.items():
            dest = where[key]
            filed, not_filed, open_groups = await self._existing(dest, members)
            plan = plan_filing(
                members,
                grouping=sel.grouping,
                filed=filed | not_filed,
                open_groups=open_groups,
            )
            stuck = sum(1 for v in members if (v.target_id, v.fingerprint) in not_filed)
            out.append((dest, plan, stuck))
        names = await target_names(self.session, {v.target_id for v in vulns})
        return out, None, names

    async def _existing(
        self, dest: Destination, vulns: list[Vulnerability]
    ) -> tuple[
        set[tuple[uuid.UUID, str]],
        set[tuple[uuid.UUID, str]],
        dict[tuple[uuid.UUID, str], OpenIssue],
    ]:
        targets = {v.target_id for v in vulns}
        linked = await self.session.execute(
            select(
                TrackedIssueFinding.target_id,
                TrackedIssueFinding.fingerprint,
                TrackedIssue.state,
            )
            .join(TrackedIssue, TrackedIssue.id == TrackedIssueFinding.issue_id)
            .where(
                TrackedIssueFinding.tracker_id == dest.tracker.id,
                TrackedIssueFinding.target_id.in_(targets),
                TrackedIssueFinding.fingerprint.in_({v.fingerprint for v in vulns}),
            )
        )
        filed: set[tuple[uuid.UUID, str]] = set()
        not_filed: set[tuple[uuid.UUID, str]] = set()
        for target_id, fingerprint, state in linked.all():
            bucket = not_filed if state == FilingState.FAILED.value else filed
            bucket.add((target_id, fingerprint))
        located = (
            select(func.count())
            .where(TrackedIssueFinding.issue_id == TrackedIssue.id)
            .correlate(TrackedIssue)
            .scalar_subquery()
        )
        rows = await self.session.execute(
            select(TrackedIssue, located)
            .where(
                TrackedIssue.tracker_id == dest.tracker.id,
                TrackedIssue.destination == dest.destination,
                TrackedIssue.grouped.is_(True),
                TrackedIssue.state.in_(_OPEN_STATES),
                TrackedIssue.remote_category.is_distinct_from(
                    RemoteCategory.DONE.value
                ),
                TrackedIssue.remote_status.is_distinct_from(NOT_FOUND),
                TrackedIssue.target_id.in_(targets),
                TrackedIssue.template_id.in_({v.template_id for v in vulns}),
            )
            .order_by(TrackedIssue.created_at.desc())
        )
        open_groups: dict[tuple[uuid.UUID, str], OpenIssue] = {}
        for issue, n in rows.all():
            open_groups.setdefault(
                (issue.target_id, issue.template_id),
                OpenIssue(issue.id, issue.external_key, int(n or 0)),
            )
        return filed, not_filed, open_groups

    async def plan(self, scope: ScopeLike, sel: FileSelection) -> FilingPlan:
        plans, refusal, names = await self._plan(scope, sel)
        result = FilingPlan(
            tracker_id=None,
            tracker_name=None,
            destination=None,
            issue_type=None,
            grouping=sel.grouping.value,
            refusal=refusal,
        )
        if len(plans) == 1:
            dest = plans[0][0]
            result.tracker_id = dest.tracker.id
            result.tracker_name = dest.tracker.name
            result.tracker_kind = dest.tracker.kind
            result.destination = dest.destination
            result.issue_type = dest.issue_type
        for dest, plan, stuck in plans:
            result.already_filed += plan.already_filed - stuck
            result.not_filed += stuck
            result.findings += plan.findings
            result.new_issues += len(plan.new)
            result.attached += sum(len(a.vulns) for a in plan.attach)
            for issue in plan.new:
                target_value = names.get(issue.target_id, "")
                result.issues.append(
                    PlannedIssue(
                        tracker_name=dest.tracker.name,
                        destination=dest.destination,
                        title=bodies.title_for(
                            issue.vulns, target_value, grouped=issue.grouped
                        ),
                        severity=issue.severity,
                        grouped=issue.grouped,
                        findings=len(issue.vulns),
                        target_value=target_value,
                    )
                )
            for attach in plan.attach:
                lead = attach.vulns[0]
                result.issues.append(
                    PlannedIssue(
                        tracker_name=dest.tracker.name,
                        destination=dest.destination,
                        title=bodies.title_for(
                            attach.vulns, names.get(lead.target_id, ""), grouped=True
                        ),
                        severity=lead.severity,
                        grouped=True,
                        findings=len(attach.vulns),
                        target_value=names.get(lead.target_id, ""),
                        attach_to=attach.issue.key or "",
                    )
                )
        single = [(dest, issue) for dest, plan, _ in plans for issue in plan.new]
        if len(single) == 1 and result.attached == 0:
            dest, issue = single[0]
            for vuln in issue.vulns[:1]:
                await self.session.refresh(vuln, ["request", "response"])
            doc = bodies.issue_body(
                issue.vulns,
                names.get(issue.target_id, ""),
                TRACKERS_BY_KIND[dest.tracker.kind],
                grouped=issue.grouped,
            )
            result.preview = [
                PreviewBlock(
                    kind=block.kind,
                    text=block.text,
                    items=[list(pair) for pair in block.items],
                    lines=block.lines,
                    href=block.href,
                    lang=block.lang,
                )
                for block in doc.blocks
            ]
        return result

    async def file(
        self, scope: ScopeLike, sel: FileSelection, user_id: uuid.UUID
    ) -> FilingResult:
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(:key)"), {"key": locks.ISSUE_FILING}
        )
        plans, refusal, names = await self._plan(scope, sel)
        if refusal:
            await self.session.rollback()
            raise _bad(refusal)
        result = FilingResult()
        created: list[TrackedIssue] = []
        dispatch: set[uuid.UUID] = set()
        touched: set[uuid.UUID] = set()
        lone = sum(len(plan.new) for _, plan, _ in plans) == 1
        try:
            for dest, plan, stuck in plans:
                result.already_filed += plan.already_filed - stuck
                result.not_filed += stuck
                for issue in plan.new:
                    lead = issue.vulns[0]
                    title = bodies.title_for(
                        issue.vulns,
                        names.get(issue.target_id, ""),
                        grouped=issue.grouped,
                    )
                    if lone and sel.title and sel.title.strip():
                        title = sel.title.strip()
                    row = TrackedIssue(
                        tracker_id=dest.tracker.id,
                        project_id=lead.project_id,
                        target_id=issue.target_id,
                        template_id=issue.template_id,
                        severity=issue.severity,
                        grouped=issue.grouped,
                        destination=dest.destination,
                        issue_type=dest.issue_type,
                        title=title,
                        created_by=user_id,
                    )
                    self.session.add(row)
                    await self.session.flush()
                    created.append(row)
                    self._link(row.id, dest, issue.vulns)
                    dispatch.add(row.id)
                    touched.add(issue.target_id)
                for attach in plan.attach:
                    self._link(attach.issue.id, dest, attach.vulns)
                    dispatch.add(attach.issue.id)
                    touched.add(attach.vulns[0].target_id)
                    result.attached += len(attach.vulns)
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Findings in this selection are being filed.",
            ) from None
        result.new_issues = len(created)
        if dispatch:
            dispatch_issue_filing([str(i) for i in dispatch])
        if touched:
            await lead_cache.bump(touched)
        result.issues = await self._reads([row.id for row in created])
        return result

    def _link(
        self, issue_id: uuid.UUID, dest: Destination, vulns: list[Vulnerability]
    ) -> None:
        for vuln in vulns:
            self.session.add(
                TrackedIssueFinding(
                    issue_id=issue_id,
                    tracker_id=dest.tracker.id,
                    target_id=vuln.target_id,
                    fingerprint=vuln.fingerprint,
                    matched_at=vuln.matched_at,
                    severity=vuln.severity,
                )
            )

    async def _reads(self, ids: list[uuid.UUID]) -> list[TrackedIssueRead]:
        if not ids:
            return []
        return await self._list(TrackedIssue.id.in_(ids))

    async def _list(self, *where) -> list[TrackedIssueRead]:
        mine = TrackedIssueFinding.issue_id == TrackedIssue.id
        total = (
            select(func.count()).where(mine).correlate(TrackedIssue).scalar_subquery()
        )
        present = (
            select(func.count())
            .where(mine, TrackedIssueFinding.present.is_(True))
            .correlate(TrackedIssue)
            .scalar_subquery()
        )
        rows = (
            await self.session.execute(
                select(TrackedIssue, IssueTracker, total, present)
                .join(IssueTracker, IssueTracker.id == TrackedIssue.tracker_id)
                .where(*where)
                .order_by(TrackedIssue.created_at.desc())
                .limit(MAX_LISTED)
            )
        ).all()
        names = await target_names(self.session, (r[0].target_id for r in rows))
        return [
            TrackedIssueRead(
                id=issue.id,
                tracker_id=tracker.id,
                tracker_name=tracker.name,
                tracker_kind=tracker.kind,
                target_id=issue.target_id,
                target_value=names.get(issue.target_id),
                template_id=issue.template_id,
                severity=issue.severity,
                grouped=issue.grouped,
                destination=issue.destination,
                title=issue.title,
                state=issue.state,
                external_key=issue.external_key,
                url=issue.url,
                remote_status=issue.remote_status,
                remote_category=issue.remote_category,
                error=issue.error,
                findings=int(n or 0),
                present=int(present or 0),
                created_at=issue.created_at,
                filed_at=issue.filed_at,
                status_read_at=issue.status_read_at,
            )
            for issue, tracker, n, present in rows
        ]

    async def list(
        self,
        project_id: uuid.UUID,
        *,
        state: str | None = None,
        tracker_id: uuid.UUID | None = None,
    ) -> list[TrackedIssueRead]:
        where = [TrackedIssue.project_id == project_id]
        if state:
            where.append(TrackedIssue.state == state)
        if tracker_id:
            where.append(TrackedIssue.tracker_id == tracker_id)
        return await self._list(*where)

    async def _issue(self, id: uuid.UUID) -> TrackedIssue:
        row = await self.session.get(TrackedIssue, id)
        if row is None:
            raise _missing(_ISSUE_MISSING)
        return row

    async def retry(self, id: uuid.UUID) -> TrackedIssueRead:
        row = await self._issue(id)
        if row.state != FilingState.FAILED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=_NOT_RETRYABLE
            )
        row.state = FilingState.PENDING.value
        row.error = None
        row.updated_at = utc_now()
        await self.session.commit()
        dispatch_issue_filing([str(row.id)])
        await lead_cache.bump([row.target_id])
        return (await self._reads([row.id]))[0]

    async def unlink(self, id: uuid.UUID) -> None:
        row = await self._issue(id)
        target_id = row.target_id
        await self.session.delete(row)
        await self.session.commit()
        await lead_cache.bump([target_id])

    async def refresh(self, id: uuid.UUID) -> TrackedIssueRead:
        row = await self._issue(id)
        fresh = row.status_read_at and row.status_read_at > utc_now() - timedelta(
            seconds=SHEET_REFRESH_SECONDS
        )
        if row.state != FilingState.FILED.value or not row.external_id or fresh:
            return (await self._reads([row.id]))[0]
        tracker = await self.session.get(IssueTracker, row.tracker_id)
        if tracker is None or not tracker.is_active:
            return (await self._reads([row.id]))[0]
        client = tracker_client(tracker)
        try:
            found = await _run(
                client, client.statuses, row.destination, [row.external_id]
            )
        except TrackerError:
            return (await self._reads([row.id]))[0]
        status_now = found.get(row.external_id)
        name = status_now.name if status_now else NOT_FOUND
        category = status_now.category if status_now else None
        moved = (name, category) != (row.remote_status, row.remote_category)
        row.remote_status = name
        row.remote_category = category
        if category != RemoteCategory.DONE.value:
            row.done_noted = False
        row.status_read_at = utc_now()
        await self.session.commit()
        if moved:
            await lead_cache.bump([row.target_id])
        return (await self._reads([row.id]))[0]
