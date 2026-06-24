import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from shared.definitions.schedule_constants import MAX_SCHEDULE_TARGETS
from shared.enums.scan_schedule import ScheduleStatus
from shared.utils.datetime import utc_now


class ScanSchedule(SQLModel, table=True):
    __tablename__ = "scan_schedules"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)
    name: str = Field(max_length=200)
    target_ids: list = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    engine_id: uuid.UUID = Field(index=True)
    engine_name: str = Field(max_length=200)
    context_id: uuid.UUID | None = Field(default=None)
    context_name: str | None = Field(default=None, max_length=200)

    schedule_type: str = Field(index=True)
    run_at: datetime | None = Field(default=None)
    interval_every: int | None = Field(default=None)
    interval_unit: str | None = Field(default=None, max_length=10)
    daily_at_time: str | None = Field(default=None, max_length=5)
    cron_expression: str | None = Field(default=None, max_length=120)
    timezone: str = Field(default="UTC", max_length=64)

    status: str = Field(default=ScheduleStatus.ACTIVE.value, index=True)
    next_run_at: datetime | None = Field(default=None, index=True)
    last_run_at: datetime | None = Field(default=None)
    last_error: str | None = Field(default=None, max_length=2000)
    total_run_count: int = Field(default=0)

    created_by: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ScheduleTargetRef(BaseModel):
    id: uuid.UUID
    target_value: str
    target_type: str


class ScanScheduleCreate(BaseModel):
    name: str
    target_ids: list[uuid.UUID] = Field(min_length=1, max_length=MAX_SCHEDULE_TARGETS)
    engine_id: uuid.UUID
    context_id: uuid.UUID | None = None
    schedule_type: str
    run_at: datetime | None = None
    interval_every: int | None = None
    interval_unit: str | None = None
    daily_at_time: str | None = None
    cron_expression: str | None = None


class ScanScheduleUpdate(BaseModel):
    name: str | None = None
    target_ids: list[uuid.UUID] | None = Field(
        default=None, min_length=1, max_length=MAX_SCHEDULE_TARGETS
    )
    engine_id: uuid.UUID | None = None
    context_id: uuid.UUID | None = None
    schedule_type: str | None = None
    run_at: datetime | None = None
    interval_every: int | None = None
    interval_unit: str | None = None
    daily_at_time: str | None = None
    cron_expression: str | None = None


class ScanScheduleRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    target_ids: list[uuid.UUID]
    targets: list[ScheduleTargetRef]
    engine_id: uuid.UUID
    engine_name: str
    context_id: uuid.UUID | None
    context_name: str | None
    schedule_type: str
    run_at: datetime | None
    interval_every: int | None
    interval_unit: str | None
    daily_at_time: str | None
    cron_expression: str | None
    timezone: str
    status: str
    next_run_at: datetime | None
    last_run_at: datetime | None
    last_error: str | None
    total_run_count: int
    cadence: str
    timezone_stale: bool = False
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
