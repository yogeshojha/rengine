"""Program watches: create, configure, read the ledger, mark seen."""

from __future__ import annotations

import contextlib
import json
import re
import uuid
from datetime import datetime
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.bounty_program import BountyProgramService
from app.services.scan import ScanService
from app.services.scan_context import ScanContextService
from app.services.scan_schedule import ScanScheduleService
from shared.config import BaseAppSettings
from shared.definitions.schedule_constants import MAX_SCHEDULE_TARGETS
from shared.definitions.watch import (
    ARRIVED_STATES,
    CADENCE_INTERVAL,
    CT_STATUS_KEY,
    EVENT_LABELS,
    FIELD_LABELS,
    HOST_STATE_LABELS,
    MAX_LISTED_ITEMS,
    WATCH_TAG,
    WatchCadence,
    WatchEventKind,
    WatchHostState,
    WatchStatus,
    mark_key,
    plan_scope,
)
from shared.enums.scan import SCAN_LIVE_STATUSES
from shared.enums.scan_schedule import ScheduleStatus, ScheduleType
from shared.models.bounty_program import BountyImportRequest, BountyProgram, BountyScope
from shared.models.notification_channel import NotificationChannel
from shared.models.scan import Scan, ScanCreate
from shared.models.scan_context import ScanContextCreate
from shared.models.scan_engine import ScanEngine
from shared.models.scan_schedule import (
    ScanSchedule,
    ScanScheduleCreate,
    ScanScheduleUpdate,
)
from shared.models.target import Target, TargetOrganization
from shared.models.watch import (
    ProgramWatch,
    StreamStatus,
    UserMark,
    WatchBaseline,
    WatchCreate,
    WatchEvent,
    WatchEventRead,
    WatchHost,
    WatchHostCounts,
    WatchHostRead,
    WatchPreview,
    WatchRead,
    WatchTargetPreview,
    WatchUpdate,
)
from shared.services.asset_query import (
    QueryContext,
    QueryScope,
    QuerySyntaxError,
    compile_query,
    parse_query,
)
from shared.services.celery_dispatch import dispatch_watch_reconcile
from shared.utils.datetime import utc_now

_SCOPE_KINDS = (WatchEventKind.SCOPE_ADDED.value, WatchEventKind.SCOPE_REMOVED.value)


def _plural(n: int, noun: str) -> str:
    return f"{n} {noun}" if n == 1 else f"{n} {noun}s"


def _bad(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _duplicate() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="This program is already watched in the project.",
    )


def _missing() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Watch not found."
    )


def validate_alert_query(query: str) -> str | None:
    """The message a bad query gets, or None."""
    if not query.strip():
        return None
    try:
        compile_query(
            parse_query(query),
            QueryContext(scope=QueryScope((uuid.uuid4(),)), now=utc_now()),
        )
    except QuerySyntaxError as exc:
        return exc.message
    return None


class WatchService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.programs = BountyProgramService(session)

    # ---------- lookups ----------

    async def ensure(self, watch_id: UUID, project_id: UUID) -> ProgramWatch:
        return await self._watch(watch_id, project_id)

    async def _watch(self, watch_id: UUID, project_id: UUID) -> ProgramWatch:
        row = await self.session.get(ProgramWatch, watch_id)
        if row is None or row.project_id != project_id:
            raise _missing()
        return row

    async def _scopes(self, program_id: UUID) -> list[BountyScope]:
        rows = await self.session.execute(
            select(BountyScope).where(BountyScope.program_id == program_id)
        )
        return list(rows.scalars().all())

    async def _existing(
        self, project_id: UUID, program_id: UUID
    ) -> ProgramWatch | None:
        return await self.session.scalar(
            select(ProgramWatch).where(
                ProgramWatch.project_id == project_id,
                ProgramWatch.program_id == program_id,
            )
        )

    async def _channels_exist(self, ids: list[UUID]) -> None:
        if not ids:
            return
        rows = await self.session.execute(
            select(func.count())
            .select_from(NotificationChannel)
            .where(NotificationChannel.id.in_(ids))
        )
        if (rows.scalar() or 0) != len(set(ids)):
            msg = "A chosen notification channel does not exist."
            raise _bad(msg)

    async def _engine(
        self, engine_id: UUID | None, project_id: UUID
    ) -> ScanEngine | None:
        if engine_id is None:
            return None
        engine = await self.session.get(ScanEngine, engine_id)
        if engine is None or engine.project_id != project_id:
            msg = "Engine not found."
            raise _bad(msg)
        return engine

    # ---------- preview ----------

    async def preview(
        self, platform: str, handle: str, project_id: UUID
    ) -> WatchPreview:
        program = await self.programs.get_program(platform, handle)
        plan = plan_scope(await self._scopes(program.id))
        values = [v for v, _ in plan.targets]
        existing: set[str] = set()
        if values:
            rows = await self.session.execute(
                select(Target.target_value).where(
                    Target.project_id == project_id,
                    Target.target_value.in_(values),
                )
            )
            existing = set(rows.scalars().all())
        watched = {i.target_value for i in plan.items}
        return WatchPreview(
            targets=[
                WatchTargetPreview(
                    value=v, type=k.value, exists=v in existing, watched=v in watched
                )
                for v, k in plan.targets
            ],
            wildcards=plan.wildcards,
            domains=len(plan.items) - plan.wildcards,
            items=[i.item for i in plan.items[:MAX_LISTED_ITEMS]],
            items_total=len(plan.items),
            excluded_hosts=len(plan.excluded_subdomains),
            excluded_ips=len(plan.excluded_ips),
            unenforceable=plan.unenforceable[:50],
            existing=await self._existing(project_id, program.id) is not None,
        )

    # ---------- create ----------

    async def create(
        self, platform: str, handle: str, data: WatchCreate, user_id: UUID
    ) -> WatchRead:
        program = await self.programs.get_program(platform, handle)
        if await self._existing(data.project_id, program.id) is not None:
            raise _duplicate()
        plan = plan_scope(await self._scopes(program.id))
        if not plan.items:
            msg = "The program has no in-scope domain or wildcard to watch."
            raise _bad(msg)
        if data.cadence != WatchCadence.OFF.value and data.engine_id is None:
            msg = "Choose an engine for the baseline, or set the cadence to off."
            raise _bad(msg)
        problem = validate_alert_query(data.alert_query)
        if problem:
            msg = f"Alert query rejected: {problem}"
            raise _bad(msg)
        await self._channels_exist(list(data.channel_ids))
        engine = await self._engine(data.engine_id, data.project_id)
        probe_engine = await self._engine(data.probe_engine_id, data.project_id)

        contexts = ScanContextService(self.session)
        context = await contexts.create(
            data.project_id,
            user_id,
            ScanContextCreate(
                name=f"Watch · {program.name}"[:200],
                description=f"Scope rules for the watched program @{program.handle}.",
                global_rate_limit_override=data.rate_limit,
                excluded_subdomains=plan.excluded_subdomains,
                excluded_ips=plan.excluded_ips,
            ),
        )
        try:
            watch, targets = await self._create_rows(
                program, plan, data, user_id, context.id, engine, probe_engine
            )
        except IntegrityError:
            await self.session.rollback()
            with contextlib.suppress(HTTPException):
                await contexts.delete(context.id, data.project_id)
            raise _duplicate() from None
        except ValidationError as exc:
            await self.session.rollback()
            with contextlib.suppress(HTTPException):
                await contexts.delete(context.id, data.project_id)
            msg = f"Watch not created: {exc.errors()[0].get('msg', 'invalid input')}"
            raise _bad(msg) from exc
        except HTTPException:
            await self.session.rollback()
            with contextlib.suppress(HTTPException):
                await contexts.delete(context.id, data.project_id)
            raise

        if data.run_baseline_now and engine is not None and targets:
            launched = await self._launch_baseline(
                watch, engine, context.id, targets[:MAX_SCHEDULE_TARGETS], user_id
            )
            self.session.add(
                WatchEvent(
                    watch_id=watch.id,
                    project_id=watch.project_id,
                    kind=WatchEventKind.BASELINE_QUEUED.value,
                    detail=f"{launched} scans queued with {engine.name}.",
                )
            )
            await self.session.commit()
        return await self.get(watch.id, data.project_id, user_id)

    async def _create_rows(
        self,
        program: BountyProgram,
        plan,
        data: WatchCreate,
        user_id: UUID,
        context_id: UUID,
        engine: ScanEngine | None,
        probe_engine: ScanEngine | None,
    ) -> tuple[ProgramWatch, list[Target]]:
        """Targets, schedule and the watch row in one transaction."""
        imported = await self.programs.import_scopes(
            program.platform,
            program.handle,
            BountyImportRequest(
                project_id=data.project_id,
                group_by_program=True,
                tags=[program.platform, WATCH_TAG],
            ),
            user_id,
        )
        targets = await self._targets_for(data.project_id, [v for v, _ in plan.targets])

        schedule_id = None
        scheduled = targets[:MAX_SCHEDULE_TARGETS]
        if engine is not None and data.cadence != WatchCadence.OFF.value and targets:
            every, unit = CADENCE_INTERVAL[data.cadence]
            sched = await ScanScheduleService(self.session).create(
                ScanScheduleCreate(
                    name=f"Watch · {program.name}"[:200],
                    target_ids=[t.id for t in scheduled],
                    engine_id=engine.id,
                    context_id=context_id,
                    intensity=data.intensity,
                    schedule_type=ScheduleType.INTERVAL.value,
                    interval_every=every,
                    interval_unit=unit,
                ),
                data.project_id,
                user_id,
            )
            schedule_id = sched.id

        watch = ProgramWatch(
            project_id=data.project_id,
            program_id=program.id,
            organization_id=imported.organization.id if imported.organization else None,
            context_id=context_id,
            schedule_id=schedule_id,
            status=WatchStatus.ACTIVE.value,
            engine_id=engine.id if engine else None,
            cadence=data.cadence,
            intensity=data.intensity,
            rate_limit=data.rate_limit,
            probe_on_resolve=data.probe_on_resolve,
            probe_engine_id=probe_engine.id if probe_engine else None,
            follow_scope=data.follow_scope,
            alert_unresolved=data.alert_unresolved,
            alert_query=data.alert_query,
            channel_ids=[str(c) for c in data.channel_ids],
            notify_in_app=data.notify_in_app,
            watch_items=[i.to_dict() for i in plan.items],
            unenforceable=plan.unenforceable[:50],
            created_by=user_id,
        )
        if len(targets) > MAX_SCHEDULE_TARGETS:
            watch.last_error = (
                f"{len(targets)} targets exceed the schedule cap of "
                f"{MAX_SCHEDULE_TARGETS}. The baseline covers the first "
                f"{MAX_SCHEDULE_TARGETS}."
            )
        self.session.add(watch)
        await self.session.flush()
        self.session.add(
            WatchEvent(
                watch_id=watch.id,
                project_id=watch.project_id,
                kind=WatchEventKind.WATCH_STARTED.value,
                detail=", ".join(
                    [
                        _plural(len(targets), "target"),
                        _plural(plan.wildcards, "wildcard") + " watched",
                        _plural(
                            len(plan.excluded_subdomains) + len(plan.excluded_ips),
                            "exclusion",
                        ),
                    ]
                )
                + ".",
            )
        )
        await self.session.commit()
        return watch, targets

    async def _targets_for(self, project_id: UUID, values: list[str]) -> list[Target]:
        if not values:
            return []
        rows = await self.session.execute(
            select(Target).where(
                Target.project_id == project_id, Target.target_value.in_(values)
            )
        )
        by_value = {t.target_value: t for t in rows.scalars().all()}
        return [by_value[v] for v in values if v in by_value]

    async def _launch_baseline(
        self,
        watch: ProgramWatch,
        engine: ScanEngine,
        context_id: UUID | None,
        targets: list[Target],
        user_id: UUID,
    ) -> int:
        if watch.schedule_id is not None:
            sched = await self.session.get(ScanSchedule, watch.schedule_id)
            if sched is not None:
                sched.next_run_at = utc_now()
                await self.session.commit()
                return len(targets)
        scans = ScanService(self.session)
        launched = 0
        for target in targets:
            try:
                await scans.create(
                    ScanCreate(
                        engine_id=engine.id,
                        context_id=context_id,
                        target_id=target.id,
                        intensity=watch.intensity,
                    ),
                    watch.project_id,
                    user_id,
                    schedule_id=watch.schedule_id,
                    schedule_type=ScheduleType.INTERVAL.value
                    if watch.schedule_id
                    else None,
                )
                launched += 1
            except HTTPException as exc:
                watch.last_error = f"{target.target_value}: {exc.detail}"[:500]
        return launched

    # ---------- read ----------

    async def _marks(
        self, user_id: UUID, watch_ids: list[UUID]
    ) -> dict[UUID, datetime]:
        if not watch_ids:
            return {}
        keys = {mark_key(w): w for w in watch_ids}
        rows = await self.session.execute(
            select(UserMark.key, UserMark.marked_at).where(
                UserMark.user_id == user_id, UserMark.key.in_(list(keys))
            )
        )
        return {keys[k]: at for k, at in rows.all()}

    async def _reads(
        self, watches: list[ProgramWatch], user_id: UUID
    ) -> list[WatchRead]:
        if not watches:
            return []
        ids = [w.id for w in watches]
        marks = await self._marks(user_id, ids)
        programs = {
            p.id: p
            for p in (
                await self.session.execute(
                    select(BountyProgram).where(
                        BountyProgram.id.in_([w.program_id for w in watches])
                    )
                )
            ).scalars()
        }
        schedules = {
            s.id: s
            for s in (
                await self.session.execute(
                    select(ScanSchedule).where(
                        ScanSchedule.id.in_(
                            [w.schedule_id for w in watches if w.schedule_id]
                        )
                    )
                )
            ).scalars()
        }
        running: dict[UUID, int] = {}
        if schedules:
            rows = await self.session.execute(
                select(Scan.schedule_id, func.count())
                .where(
                    Scan.schedule_id.in_(list(schedules)),
                    Scan.status.in_(SCAN_LIVE_STATUSES),
                )
                .group_by(Scan.schedule_id)
            )
            running = dict(rows.all())
        target_counts: dict[UUID, int] = {}
        org_ids = [w.organization_id for w in watches if w.organization_id]
        if org_ids:
            rows = await self.session.execute(
                select(TargetOrganization.organization_id, func.count())
                .where(TargetOrganization.organization_id.in_(org_ids))
                .group_by(TargetOrganization.organization_id)
            )
            target_counts = dict(rows.all())

        since = await self._since_many(marks, ids)
        ledger = await self._ledger_totals(ids)
        out: list[WatchRead] = []
        for w in watches:
            mark = marks.get(w.id)
            new_hosts, new_alerts, scope_changes = since[w.id]
            program = programs.get(w.program_id)
            sched = schedules.get(w.schedule_id) if w.schedule_id else None
            out.append(
                WatchRead(
                    id=w.id,
                    project_id=w.project_id,
                    program_id=w.program_id,
                    platform=program.platform if program else "",
                    handle=program.handle if program else "",
                    program_name=program.name if program else "",
                    profile_picture=program.profile_picture if program else None,
                    submission_state=program.submission_state if program else "unknown",
                    status=w.status,
                    organization_id=w.organization_id,
                    context_id=w.context_id,
                    engine_id=w.engine_id,
                    cadence=w.cadence,
                    intensity=w.intensity,
                    rate_limit=w.rate_limit,
                    probe_on_resolve=w.probe_on_resolve,
                    probe_engine_id=w.probe_engine_id,
                    follow_scope=w.follow_scope,
                    alert_unresolved=w.alert_unresolved,
                    alert_query=w.alert_query,
                    channel_ids=[UUID(str(c)) for c in (w.channel_ids or [])],
                    notify_in_app=w.notify_in_app,
                    watch_items=[
                        str(i.get("item"))
                        for i in (w.watch_items or [])[:MAX_LISTED_ITEMS]
                    ],
                    items_total=len(w.watch_items or []),
                    unenforceable=list(w.unenforceable or []),
                    targets=target_counts.get(w.organization_id, 0)
                    if w.organization_id
                    else 0,
                    hosts_seen=ledger.get(w.id, (0, 0))[0],
                    hosts_alerted=ledger.get(w.id, (0, 0))[1],
                    last_certificate_at=w.last_certificate_at,
                    last_alert_at=w.last_alert_at,
                    last_error=w.last_error,
                    baseline=WatchBaseline(
                        schedule_id=sched.id if sched else None,
                        engine_name=sched.engine_name if sched else None,
                        status=sched.status if sched else None,
                        next_run_at=sched.next_run_at if sched else None,
                        last_run_at=sched.last_run_at if sched else None,
                        running=running.get(sched.id, 0) if sched else 0,
                    ),
                    seen_at=mark,
                    new_hosts=new_hosts,
                    new_alerts=new_alerts,
                    scope_changes=scope_changes,
                    created_at=w.created_at,
                    updated_at=w.updated_at,
                )
            )
        return out

    async def _ledger_totals(
        self, watch_ids: list[UUID]
    ) -> dict[UUID, tuple[int, int]]:
        rows = await self.session.execute(
            select(
                WatchHost.watch_id,
                func.count(),
                func.count(WatchHost.alerted_at),
            )
            .where(WatchHost.watch_id.in_(watch_ids))
            .group_by(WatchHost.watch_id)
        )
        return {wid: (seen, alerted) for wid, seen, alerted in rows.all()}

    async def _since_many(
        self, marks: dict[UUID, datetime | None], watch_ids: list[UUID]
    ) -> dict[UUID, tuple[int, int, int]]:
        """Arrived hosts, alerts and scope changes per watch since its mark."""

        def after(model, column):
            return or_(
                *[
                    and_(model.watch_id == wid, column > marks[wid])
                    if marks.get(wid) is not None
                    else model.watch_id == wid
                    for wid in watch_ids
                ]
            )

        async def counts(model, column, *extra) -> dict[UUID, int]:
            rows = await self.session.execute(
                select(model.watch_id, func.count())
                .where(model.watch_id.in_(watch_ids), after(model, column), *extra)
                .group_by(model.watch_id)
            )
            return dict(rows.all())

        hosts = await counts(
            WatchHost, WatchHost.first_seen_at, WatchHost.state.in_(ARRIVED_STATES)
        )
        alerts = await counts(
            WatchHost, WatchHost.alerted_at, WatchHost.alerted_at.isnot(None)
        )
        events = await counts(
            WatchEvent, WatchEvent.created_at, WatchEvent.kind.in_(_SCOPE_KINDS)
        )
        return {
            wid: (hosts.get(wid, 0), alerts.get(wid, 0), events.get(wid, 0))
            for wid in watch_ids
        }

    async def list(self, project_id: UUID, user_id: UUID) -> list[WatchRead]:
        rows = await self.session.execute(
            select(ProgramWatch)
            .where(ProgramWatch.project_id == project_id)
            .order_by(ProgramWatch.created_at.desc())
        )
        return await self._reads(list(rows.scalars().all()), user_id)

    async def get(self, watch_id: UUID, project_id: UUID, user_id: UUID) -> WatchRead:
        watch = await self._watch(watch_id, project_id)
        return (await self._reads([watch], user_id))[0]

    # ---------- update ----------

    async def update(
        self, watch_id: UUID, project_id: UUID, data: WatchUpdate, user_id: UUID
    ) -> WatchRead:
        watch = await self._watch(watch_id, project_id)
        fields = data.model_fields_set
        if "alert_query" in fields and data.alert_query is not None:
            problem = validate_alert_query(data.alert_query)
            if problem:
                msg = f"Alert query rejected: {problem}"
                raise _bad(msg)
            watch.alert_query = data.alert_query
        if "channel_ids" in fields and data.channel_ids is not None:
            await self._channels_exist(list(data.channel_ids))
            watch.channel_ids = [str(c) for c in data.channel_ids]
        for name in (
            "probe_on_resolve",
            "follow_scope",
            "alert_unresolved",
            "notify_in_app",
            "intensity",
        ):
            if name in fields:
                setattr(watch, name, getattr(data, name))
        if "probe_engine_id" in fields:
            probe = await self._engine(data.probe_engine_id, project_id)
            watch.probe_engine_id = probe.id if probe else None
        if "rate_limit" in fields:
            watch.rate_limit = data.rate_limit
            if watch.context_id is not None:
                await ScanContextService(self.session).set_rate_limit(
                    watch.context_id, project_id, data.rate_limit
                )
        if "engine_id" in fields or "cadence" in fields or "intensity" in fields:
            await self._apply_baseline(watch, data, project_id, user_id)
        if "status" in fields and data.status and data.status != watch.status:
            await self._set_status(watch, data.status, project_id)
        else:
            self.session.add(
                WatchEvent(
                    watch_id=watch.id,
                    project_id=watch.project_id,
                    kind=WatchEventKind.WATCH_UPDATED.value,
                    detail=", ".join(
                        FIELD_LABELS.get(f, f) for f in sorted(fields) if f != "status"
                    )[:500],
                )
            )
        watch.last_error = None
        watch.updated_at = utc_now()
        await self.session.commit()
        return await self.get(watch.id, project_id, user_id)

    async def _apply_baseline(
        self, watch: ProgramWatch, data: WatchUpdate, project_id: UUID, user_id: UUID
    ) -> None:
        fields = data.model_fields_set
        engine_id = data.engine_id if "engine_id" in fields else watch.engine_id
        cadence = data.cadence if data.cadence is not None else watch.cadence
        try:
            engine = await self._engine(engine_id, project_id)
        except HTTPException:
            if "engine_id" in fields:
                raise
            engine = None
        schedules = ScanScheduleService(self.session)
        watch.engine_id = engine.id if engine else None
        watch.cadence = cadence
        if watch.schedule_id is not None:
            sched = await self.session.get(ScanSchedule, watch.schedule_id)
            if sched is None or sched.project_id != project_id:
                watch.schedule_id = None
        if cadence == WatchCadence.OFF.value or engine is None:
            if watch.schedule_id is not None:
                with contextlib.suppress(HTTPException):
                    await schedules.delete(watch.schedule_id, project_id)
                watch.schedule_id = None
            return
        every, unit = CADENCE_INTERVAL[cadence]
        if watch.schedule_id is not None:
            await schedules.update(
                watch.schedule_id,
                project_id,
                ScanScheduleUpdate(
                    engine_id=engine.id,
                    intensity=watch.intensity,
                    schedule_type=ScheduleType.INTERVAL.value,
                    interval_every=every,
                    interval_unit=unit,
                ),
            )
            return
        program = await self.session.get(BountyProgram, watch.program_id)
        plan = plan_scope(await self._scopes(watch.program_id))
        targets = await self._targets_for(project_id, [v for v, _ in plan.targets])
        if not targets:
            return
        sched = await schedules.create(
            ScanScheduleCreate(
                name=f"Watch · {program.name if program else 'program'}"[:200],
                target_ids=[t.id for t in targets[:MAX_SCHEDULE_TARGETS]],
                engine_id=engine.id,
                context_id=watch.context_id,
                intensity=watch.intensity,
                schedule_type=ScheduleType.INTERVAL.value,
                interval_every=every,
                interval_unit=unit,
            ),
            project_id,
            user_id,
        )
        watch.schedule_id = sched.id

    async def _set_status(
        self, watch: ProgramWatch, new: str, project_id: UUID
    ) -> None:
        watch.status = new
        if watch.schedule_id is not None:
            target = (
                ScheduleStatus.ACTIVE
                if new == WatchStatus.ACTIVE.value
                else ScheduleStatus.PAUSED
            )
            try:
                await ScanScheduleService(self.session).set_status(
                    watch.schedule_id, project_id, target
                )
            except HTTPException:
                watch.schedule_id = None
        kind = (
            WatchEventKind.WATCH_RESUMED
            if new == WatchStatus.ACTIVE.value
            else WatchEventKind.WATCH_PAUSED
        )
        self.session.add(
            WatchEvent(watch_id=watch.id, project_id=watch.project_id, kind=kind.value)
        )

    async def delete(self, watch_id: UUID, project_id: UUID) -> None:
        """Remove the watch, its schedule and its context. Targets stay."""
        watch = await self._watch(watch_id, project_id)
        schedule_id, context_id = watch.schedule_id, watch.context_id
        await self.session.delete(watch)
        await self.session.commit()
        if schedule_id is not None:
            with contextlib.suppress(HTTPException):
                await ScanScheduleService(self.session).delete(schedule_id, project_id)
        if context_id is not None:
            with contextlib.suppress(HTTPException):
                await ScanContextService(self.session).delete(context_id, project_id)

    async def reconcile(self, watch_id: UUID, project_id: UUID) -> dict:
        watch = await self._watch(watch_id, project_id)
        return {"queued": dispatch_watch_reconcile(str(watch.program_id))}

    # ---------- ledger ----------

    def hosts_query(
        self,
        watch_id: UUID,
        *,
        state: str | None,
        since: datetime | None,
        q: str | None,
    ) -> Select:
        stmt = select(WatchHost).where(WatchHost.watch_id == watch_id)
        order = WatchHost.first_seen_at
        if state == "arrived":
            stmt = stmt.where(WatchHost.state.in_(ARRIVED_STATES))
        elif state == "alerted":
            stmt = stmt.where(WatchHost.alerted_at.isnot(None))
            order = WatchHost.alerted_at
        elif state == "unresolved":
            stmt = stmt.where(
                WatchHost.state.in_(
                    (WatchHostState.NEW.value, WatchHostState.UNRESOLVED.value)
                )
            )
        elif state in {s.value for s in WatchHostState}:
            stmt = stmt.where(WatchHost.state == state)
        if since is not None:
            stmt = stmt.where(order > since)
        if q:
            needle = re.sub(r"([\\%_])", r"\\\1", q.strip().lower())
            stmt = stmt.where(WatchHost.name.ilike(f"%{needle}%", escape="\\"))
        return stmt.order_by(order.desc())

    @staticmethod
    def host_read(row: WatchHost) -> WatchHostRead:
        return WatchHostRead(
            id=row.id,
            watch_id=row.watch_id,
            target_id=row.target_id,
            name=row.name,
            state=row.state,
            state_label=HOST_STATE_LABELS.get(row.state, row.state),
            reason=row.reason,
            matched_item=row.matched_item,
            issuer=row.issuer,
            not_before=row.not_before,
            sightings=row.sightings,
            first_seen_at=row.first_seen_at,
            last_seen_at=row.last_seen_at,
            resolved_ips=[str(i) for i in (row.resolved_ips or [])],
            cname=row.cname,
            is_wildcard=row.is_wildcard,
            scan_id=row.scan_id,
            probed_at=row.probed_at,
            status_code=row.status_code,
            title=row.title,
            tech=[str(t) for t in (row.tech or [])],
            screenshot_path=row.screenshot_path,
            alerted_at=row.alerted_at,
            alerts=row.alerts,
        )

    async def host_counts(
        self, watch_id: UUID, project_id: UUID, since: datetime | None
    ) -> WatchHostCounts:
        await self._watch(watch_id, project_id)
        base = select(WatchHost.state, func.count()).where(
            WatchHost.watch_id == watch_id
        )
        if since is not None:
            base = base.where(WatchHost.first_seen_at > since)
        rows = await self.session.execute(base.group_by(WatchHost.state))
        by_state = dict(rows.all())
        alerted = (
            select(func.count())
            .select_from(WatchHost)
            .where(WatchHost.watch_id == watch_id, WatchHost.alerted_at.isnot(None))
        )
        if since is not None:
            alerted = alerted.where(WatchHost.alerted_at > since)
        return WatchHostCounts(
            all=sum(by_state.values()),
            arrived=sum(by_state.get(s, 0) for s in ARRIVED_STATES),
            alerted=(await self.session.scalar(alerted)) or 0,
            unresolved=by_state.get(WatchHostState.NEW.value, 0)
            + by_state.get(WatchHostState.UNRESOLVED.value, 0),
            known=by_state.get(WatchHostState.KNOWN.value, 0),
            out_of_scope=by_state.get(WatchHostState.OUT_OF_SCOPE.value, 0),
        )

    async def mute_host(
        self, watch_id: UUID, host_id: UUID, project_id: UUID
    ) -> WatchHostRead:
        await self._watch(watch_id, project_id)
        row = await self.session.get(WatchHost, host_id)
        if row is None or row.watch_id != watch_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Host not found."
            )
        if row.state == WatchHostState.MUTED.value:
            row.state = row.muted_from or (
                WatchHostState.ALERTED.value
                if row.alerts
                else WatchHostState.QUIET.value
            )
            row.muted_from = None
            row.reason = None
        else:
            row.muted_from = row.state
            row.state = WatchHostState.MUTED.value
            row.reason = "muted"
        await self.session.commit()
        return self.host_read(row)

    def events_query(
        self, watch_id: UUID, *, kind: str | None = None, since: datetime | None = None
    ) -> Select:
        stmt = select(WatchEvent).where(WatchEvent.watch_id == watch_id)
        if kind == "scope":
            stmt = stmt.where(WatchEvent.kind.in_(_SCOPE_KINDS))
        elif kind in {k.value for k in WatchEventKind}:
            stmt = stmt.where(WatchEvent.kind == kind)
        if since is not None:
            stmt = stmt.where(WatchEvent.created_at > since)
        return stmt.order_by(WatchEvent.created_at.desc())

    @staticmethod
    def event_read(row: WatchEvent) -> WatchEventRead:
        return WatchEventRead(
            id=row.id,
            watch_id=row.watch_id,
            kind=row.kind,
            label=EVENT_LABELS.get(row.kind, row.kind),
            name=row.name,
            detail=row.detail,
            created_at=row.created_at,
        )

    # ---------- marks ----------

    async def mark_seen(
        self, watch_id: UUID, project_id: UUID, user_id: UUID
    ) -> datetime:
        await self._watch(watch_id, project_id)
        now = utc_now()
        stmt = pg_insert(UserMark).values(
            user_id=user_id, key=mark_key(watch_id), marked_at=now
        )
        await self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=["user_id", "key"], set_={"marked_at": now}
            )
        )
        await self.session.commit()
        return now

    # ---------- stream ----------

    @staticmethod
    async def stream_status() -> StreamStatus:
        client = aioredis.from_url(BaseAppSettings().redis_url, decode_responses=True)
        try:
            raw = await client.get(CT_STATUS_KEY)
        except Exception:
            return StreamStatus()
        finally:
            await client.aclose()
        if not raw:
            return StreamStatus()
        try:
            data = json.loads(raw)
        except ValueError:
            return StreamStatus()
        return StreamStatus(
            reachable=True, **{k: v for k, v in data.items() if k != "reachable"}
        )
