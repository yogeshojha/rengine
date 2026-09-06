from datetime import UTC, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.scan import ScanService
from shared.definitions.schedule_constants import MAX_INTERVAL, TIME_RE
from shared.enums.scan_schedule import (
    INTERVAL_UNITS,
    SCHEDULE_TYPES,
    ScheduleStatus,
    ScheduleType,
)
from shared.models.instance_settings import InstanceSettings
from shared.models.scan import ScanCreate, ScanRead
from shared.models.scan_context import ScanContext
from shared.models.scan_engine import ScanEngine
from shared.models.scan_schedule import (
    ScanSchedule,
    ScanScheduleCreate,
    ScanScheduleRead,
    ScanScheduleUpdate,
    ScheduleTargetRef,
)
from shared.models.target import Target
from shared.services.schedule_timing import compute_next_run_at, describe_schedule
from shared.utils.datetime import utc_now
from shared.utils.uuid import uuid_list


def _bad(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _validate_tz(tz: str) -> None:
    try:
        ZoneInfo(tz)
    except Exception as exc:
        msg = f"Instance timezone '{tz}' is invalid. Set a valid timezone in Settings."
        raise _bad(msg) from exc


class ScanScheduleService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _instance_timezone(self) -> str:
        row = (
            await self.session.execute(select(InstanceSettings).limit(1))
        ).scalar_one_or_none()
        return row.timezone if row and row.timezone else "UTC"

    async def _get(
        self, id: UUID, project_id: UUID, *, for_update: bool = False
    ) -> ScanSchedule:
        query = select(ScanSchedule).where(
            ScanSchedule.id == id, ScanSchedule.project_id == project_id
        )
        if for_update:
            query = query.with_for_update()
        row = (await self.session.execute(query)).scalar_one_or_none()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found"
            )
        return row

    async def _get_engine(self, engine_id: UUID, project_id: UUID) -> ScanEngine:
        engine = (
            await self.session.execute(
                select(ScanEngine).where(
                    ScanEngine.id == engine_id, ScanEngine.project_id == project_id
                )
            )
        ).scalar_one_or_none()
        if engine is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Scan engine not found"
            )
        return engine

    async def _get_context(
        self, context_id: UUID | None, project_id: UUID
    ) -> ScanContext | None:
        if context_id is None:
            return None
        ctx = (
            await self.session.execute(
                select(ScanContext).where(
                    ScanContext.id == context_id, ScanContext.project_id == project_id
                )
            )
        ).scalar_one_or_none()
        if ctx is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Scan context not found"
            )
        return ctx

    async def _targets(self, target_ids: list[UUID], project_id: UUID) -> list[Target]:
        if not target_ids:
            msg = "At least one target is required."
            raise _bad(msg)
        rows = (
            (
                await self.session.execute(
                    select(Target).where(
                        Target.id.in_(target_ids), Target.project_id == project_id
                    )
                )
            )
            .scalars()
            .all()
        )
        found = {t.id for t in rows}
        missing = [str(t) for t in target_ids if t not in found]
        if missing:
            msg = f"Targets not found: {', '.join(missing)}"
            raise _bad(msg)
        return list(rows)

    def _to_utc(self, dt: datetime, tz: str) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=ZoneInfo(tz)).astimezone(UTC)
        return dt.astimezone(UTC)

    def _apply_timing(self, sched: ScanSchedule, data, tz: str) -> None:
        stype = data.schedule_type
        if stype not in SCHEDULE_TYPES:
            msg = f"Invalid schedule type. One of {', '.join(SCHEDULE_TYPES)}."
            raise _bad(msg)
        sched.schedule_type = stype
        sched.run_at = None
        sched.interval_every = None
        sched.interval_unit = None
        sched.daily_at_time = None
        sched.cron_expression = None

        if stype == ScheduleType.ONE_OFF.value:
            if data.run_at is None:
                msg = "A run date/time is required for a one-off schedule."
                raise _bad(msg)
            run_at = self._to_utc(data.run_at, tz)
            if run_at <= utc_now():
                msg = "The scheduled time must be in the future."
                raise _bad(msg)
            sched.run_at = run_at
        elif stype == ScheduleType.INTERVAL.value:
            if not data.interval_every or data.interval_every < 1:
                msg = "Interval must be a positive number."
                raise _bad(msg)
            if data.interval_every > MAX_INTERVAL:
                msg = "Interval is too large."
                raise _bad(msg)
            if data.interval_unit not in INTERVAL_UNITS:
                msg = f"Invalid unit. One of {', '.join(INTERVAL_UNITS)}."
                raise _bad(msg)
            sched.interval_every = data.interval_every
            sched.interval_unit = data.interval_unit
        elif stype == ScheduleType.DAILY_AT.value:
            if not data.daily_at_time or not TIME_RE.match(data.daily_at_time):
                msg = "Time must be in HH:MM (24-hour) format."
                raise _bad(msg)
            sched.daily_at_time = data.daily_at_time
        elif stype == ScheduleType.CRON.value:
            from croniter import croniter  # noqa: PLC0415

            if not data.cron_expression or not croniter.is_valid(data.cron_expression):
                msg = "Invalid cron expression."
                raise _bad(msg)
            sched.cron_expression = data.cron_expression

    async def _targets_by_ids(self, ids: list[UUID]) -> dict[UUID, Target]:
        if not ids:
            return {}
        rows = (
            (await self.session.execute(select(Target).where(Target.id.in_(ids))))
            .scalars()
            .all()
        )
        return {t.id: t for t in rows}

    async def _read_one(self, sched: ScanSchedule) -> ScanScheduleRead:
        targets = await self._targets_by_ids(uuid_list(sched.target_ids))
        return self._to_read(sched, targets, await self._instance_timezone())

    def _to_read(
        self, sched: ScanSchedule, targets: dict[UUID, Target], current_tz: str
    ) -> ScanScheduleRead:
        target_ids = uuid_list(sched.target_ids)
        refs = [
            ScheduleTargetRef(
                id=tid,
                target_value=targets[tid].target_value,
                target_type=targets[tid].target_type.value,
            )
            for tid in target_ids
            if tid in targets
        ]
        return ScanScheduleRead(
            id=sched.id,
            project_id=sched.project_id,
            name=sched.name,
            target_ids=target_ids,
            targets=refs,
            engine_id=sched.engine_id,
            engine_name=sched.engine_name,
            context_id=sched.context_id,
            context_name=sched.context_name,
            schedule_type=sched.schedule_type,
            run_at=sched.run_at,
            interval_every=sched.interval_every,
            interval_unit=sched.interval_unit,
            daily_at_time=sched.daily_at_time,
            cron_expression=sched.cron_expression,
            timezone=sched.timezone,
            status=sched.status,
            next_run_at=sched.next_run_at,
            last_run_at=sched.last_run_at,
            last_error=sched.last_error,
            total_run_count=sched.total_run_count,
            cadence=describe_schedule(sched),
            timezone_stale=sched.timezone != current_tz,
            created_by=sched.created_by,
            created_at=sched.created_at,
            updated_at=sched.updated_at,
        )

    async def create(
        self, data: ScanScheduleCreate, project_id: UUID, created_by: UUID
    ) -> ScanScheduleRead:
        tz = await self._instance_timezone()
        _validate_tz(tz)
        engine = await self._get_engine(data.engine_id, project_id)
        context = await self._get_context(data.context_id, project_id)
        targets = await self._targets(data.target_ids, project_id)

        sched = ScanSchedule(
            project_id=project_id,
            name=data.name.strip() or "Schedule",
            target_ids=[str(t.id) for t in targets],
            engine_id=engine.id,
            engine_name=engine.name,
            context_id=context.id if context is not None else None,
            context_name=context.name if context is not None else None,
            timezone=tz,
            status=ScheduleStatus.ACTIVE.value,
            created_by=created_by,
        )
        self._apply_timing(sched, data, tz)
        sched.next_run_at = compute_next_run_at(sched)
        self.session.add(sched)
        await self.session.commit()
        await self.session.refresh(sched)
        return self._to_read(sched, {t.id: t for t in targets}, tz)

    async def list_schedules(self, project_id: UUID) -> list[ScanScheduleRead]:
        rows = (
            (
                await self.session.execute(
                    select(ScanSchedule)
                    .where(ScanSchedule.project_id == project_id)
                    .order_by(ScanSchedule.created_at.desc())
                )
            )
            .scalars()
            .all()
        )
        all_ids = [tid for s in rows for tid in uuid_list(s.target_ids)]
        targets = await self._targets_by_ids(list(set(all_ids)))
        current_tz = await self._instance_timezone()
        return [self._to_read(s, targets, current_tz) for s in rows]

    async def get(self, id: UUID, project_id: UUID) -> ScanScheduleRead:
        sched = await self._get(id, project_id)
        return await self._read_one(sched)

    async def update(
        self, id: UUID, project_id: UUID, data: ScanScheduleUpdate
    ) -> ScanScheduleRead:
        sched = await self._get(id, project_id, for_update=True)

        if data.name is not None:
            sched.name = data.name.strip() or sched.name
        if data.engine_id is not None:
            engine = await self._get_engine(data.engine_id, project_id)
            sched.engine_id = engine.id
            sched.engine_name = engine.name
        if data.context_id is not None or "context_id" in data.model_fields_set:
            context = await self._get_context(data.context_id, project_id)
            sched.context_id = context.id if context is not None else None
            sched.context_name = context.name if context is not None else None
        if data.target_ids is not None:
            targets = await self._targets(data.target_ids, project_id)
            sched.target_ids = [str(t.id) for t in targets]

        if data.schedule_type is not None:
            self._apply_timing(sched, data, sched.timezone)
            if sched.status != ScheduleStatus.COMPLETED.value:
                sched.next_run_at = compute_next_run_at(sched)

        sched.updated_at = utc_now()
        await self.session.commit()
        await self.session.refresh(sched)
        return await self._read_one(sched)

    async def set_status(
        self, id: UUID, project_id: UUID, new_status: ScheduleStatus
    ) -> ScanScheduleRead:
        sched = await self._get(id, project_id, for_update=True)
        sched.status = new_status.value
        if new_status == ScheduleStatus.ACTIVE:
            nxt = compute_next_run_at(sched)
            if nxt is None and sched.schedule_type == ScheduleType.ONE_OFF.value:
                sched.status = ScheduleStatus.COMPLETED.value
            sched.next_run_at = nxt
        sched.updated_at = utc_now()
        await self.session.commit()
        await self.session.refresh(sched)
        return await self._read_one(sched)

    async def run_now(
        self, id: UUID, project_id: UUID, created_by: UUID
    ) -> list[ScanRead]:
        sched = await self._get(id, project_id, for_update=True)
        scan_service = ScanService(self.session)
        spawned: list[ScanRead] = []
        errors: list[str] = []
        for t in uuid_list(sched.target_ids):
            try:
                scan = await scan_service.create(
                    ScanCreate(
                        engine_id=sched.engine_id,
                        context_id=sched.context_id,
                        target_id=t,
                    ),
                    project_id=project_id,
                    created_by=created_by,
                    schedule_id=sched.id,
                    schedule_type=sched.schedule_type,
                )
                spawned.append(scan)
            except HTTPException as exc:
                errors.append(f"{t}: {exc.detail}")
        if not spawned:
            msg = "No scans could be launched for this schedule."
            raise _bad(msg)
        sched.last_run_at = utc_now()
        sched.total_run_count += 1
        sched.last_error = "; ".join(errors)[:2000] if errors else None
        await self.session.commit()
        return spawned

    async def delete(self, id: UUID, project_id: UUID) -> None:
        sched = await self._get(id, project_id)
        await self.session.delete(sched)
        await self.session.commit()
