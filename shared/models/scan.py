import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from shared.enums.scan import ScanStatus
from shared.services.scan_resolve import ResolvedScanConfig
from shared.utils.datetime import utc_now

SCAN_STATUSES = tuple(s.value for s in ScanStatus)


class Scan(SQLModel, table=True):
    __tablename__ = "scans"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)
    target_id: uuid.UUID = Field(
        foreign_key="targets.id", index=True, ondelete="CASCADE"
    )
    engine_id: uuid.UUID = Field(index=True)
    engine_name: str = Field(max_length=200)
    context_id: uuid.UUID | None = Field(default=None)
    context_name: str | None = Field(default=None, max_length=200)
    schedule_id: uuid.UUID | None = Field(default=None, index=True)
    schedule_type: str | None = Field(default=None, max_length=20)
    execution_config: dict = Field(sa_column=Column(JSON, nullable=False))
    status: str = Field(default=ScanStatus.PENDING.value, index=True)
    celery_task_ids: list = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    subdomains_found: int = Field(default=0)
    ips_found: int = Field(default=0)
    open_ports_found: int = Field(default=0)
    vulnerabilities_found: int = Field(default=0)
    endpoints_found: int = Field(default=0)
    error: str | None = Field(default=None, max_length=2000)
    created_by: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)


class ScanCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    engine_id: uuid.UUID
    context_id: uuid.UUID | None = None
    target_id: uuid.UUID


class ScanRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    target_id: uuid.UUID
    engine_id: uuid.UUID
    engine_name: str
    context_id: uuid.UUID | None
    context_name: str | None
    schedule_id: uuid.UUID | None = None
    schedule_type: str | None = None
    execution_config: ResolvedScanConfig
    auth_summary: str
    status: str
    subdomains_found: int
    ips_found: int
    open_ports_found: int
    vulnerabilities_found: int
    endpoints_found: int
    error: str | None
    created_by: uuid.UUID
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    duration_seconds: float | None = None
    new_subdomains: int | None = None
    gone_subdomains: int | None = None
    prev_subdomains_found: int | None = None
    is_first_scan: bool | None = None


class ScanStatusCounts(BaseModel):
    pending: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0


class ScanDailyCount(BaseModel):
    date: str
    count: int
    completed: int = 0
    failed: int = 0
    cancelled: int = 0
    running: int = 0
    pending: int = 0


class ScanFacet(BaseModel):
    name: str
    count: int


class ScanChanges(BaseModel):
    window: str
    new_subdomains: int
    retired_subdomains: int = 0
    targets_changed: int
    scans_run: int
    failed_runs: int


class ScanTargetGroup(BaseModel):
    target_id: uuid.UUID
    target_value: str
    target_type: str
    scan_count: int
    last_scan_at: datetime
    last_status: str
    running: int
    trend: list[int] = []


class ScanExportRow(BaseModel):
    target: str
    status: str
    engine: str
    context: str | None
    schedule_type: str | None = None
    subdomains: int
    ips: int
    open_ports: int
    vulnerabilities: int
    endpoints: int
    duration_seconds: float | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class ScanStats(BaseModel):
    total: int
    running: int
    by_status: ScanStatusCounts
    last_scan_at: datetime | None
    avg_duration_seconds: float | None
    success_rate: float | None
    daily: list[ScanDailyCount]
    engines: list[ScanFacet] = []
    contexts: list[ScanFacet] = []
