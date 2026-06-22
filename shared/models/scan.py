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
    target_id: uuid.UUID = Field(foreign_key="targets.id", index=True)
    engine_id: uuid.UUID = Field(index=True)
    engine_name: str = Field(max_length=200)
    context_id: uuid.UUID | None = Field(default=None)
    context_name: str | None = Field(default=None, max_length=200)
    execution_config: dict = Field(sa_column=Column(JSON, nullable=False))
    status: str = Field(default=ScanStatus.PENDING.value, index=True)
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


class ScanStatusCounts(BaseModel):
    pending: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0


class ScanDailyCount(BaseModel):
    date: str
    count: int


class ScanStats(BaseModel):
    total: int
    running: int
    by_status: ScanStatusCounts
    last_scan_at: datetime | None
    avg_duration_seconds: float | None
    success_rate: float | None
    daily: list[ScanDailyCount]
