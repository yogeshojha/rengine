import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator
from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from shared.definitions.constants import MAX_SCAN_BATCH
from shared.definitions.rescan import MAX_SEED_ASSETS, SeedKind
from shared.definitions.surface import SURFACE_ORDER
from shared.enums.scan import ScanScope, ScanStatus
from shared.services.scan_resolve import ResolvedScanConfig
from shared.utils.datetime import utc_now

SCAN_STATUSES = tuple(s.value for s in ScanStatus)
SCAN_SCOPES = tuple(s.value for s in ScanScope)


class SeedAsset(BaseModel):
    """One asset a focused scan starts from."""

    model_config = ConfigDict(extra="forbid")

    kind: str = Field(max_length=16)
    value: str = Field(max_length=500)

    @model_validator(mode="after")
    def _known_kind(self):
        if self.kind not in {k.value for k in SeedKind}:
            msg = f"Unknown seed kind '{self.kind}'."
            raise ValueError(msg)
        if not self.value.strip():
            msg = "Seed asset value cannot be empty."
            raise ValueError(msg)
        return self


class Scan(SQLModel, table=True):
    __tablename__ = "scans"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)
    target_id: uuid.UUID = Field(
        foreign_key="targets.id", index=True, ondelete="CASCADE"
    )
    engine_id: uuid.UUID | None = Field(default=None, index=True)
    engine_name: str = Field(max_length=200)
    context_id: uuid.UUID | None = Field(default=None)
    context_name: str | None = Field(default=None, max_length=200)
    schedule_id: uuid.UUID | None = Field(default=None, index=True)
    schedule_type: str | None = Field(default=None, max_length=20)
    scope: str = Field(default=ScanScope.FULL.value, max_length=16, index=True)
    parent_scan_id: uuid.UUID | None = Field(default=None, index=True)
    execution_config: dict = Field(sa_column=Column(JSON, nullable=False))
    status: str = Field(default=ScanStatus.PENDING.value, index=True)
    celery_task_ids: list = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    subdomains_found: int = Field(default=0)
    ips_found: int = Field(default=0)
    open_ports_found: int = Field(default=0)
    http_assets_found: int = Field(default=0)
    vulnerabilities_found: int = Field(default=0)
    endpoints_found: int = Field(default=0)
    error: str | None = Field(default=None, max_length=2000)
    created_by: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)


class ScanCreate(BaseModel):
    """A launch names a saved engine, or runs an ad hoc plan carried in `overrides`."""

    model_config = ConfigDict(extra="forbid")

    engine_id: uuid.UUID | None = None
    context_id: uuid.UUID | None = None
    target_id: uuid.UUID | None = None
    target_value: str | None = Field(default=None, max_length=500)
    overrides: dict[str, dict] = Field(default_factory=dict)
    intensity: str | None = None
    seed_assets: list[SeedAsset] = Field(
        default_factory=list, max_length=MAX_SEED_ASSETS
    )
    parent_scan_id: uuid.UUID | None = None
    dimension: str | None = Field(default=None, max_length=32)

    @model_validator(mode="after")
    def _require_target(self):
        if (self.target_id is None) == (not self.target_value):
            msg = "Provide either target_id or target_value."
            raise ValueError(msg)
        return self


class RescanCreate(BaseModel):
    """Re-run chosen stages against assets picked from an earlier run."""

    model_config = ConfigDict(extra="forbid")

    parent_scan_id: uuid.UUID
    dimension: str = Field(max_length=32)
    assets: list[str] = Field(min_length=1, max_length=MAX_SEED_ASSETS)
    stages: list[str] = Field(default_factory=list, max_length=20)
    overrides: dict[str, dict] = Field(default_factory=dict)
    context_id: uuid.UUID | None = None
    intensity: str | None = None
    template_ids: list[str] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def _known_dimension(self):
        if self.dimension not in SURFACE_ORDER:
            msg = f"Unknown dimension '{self.dimension}'."
            raise ValueError(msg)
        cleaned = [a.strip() for a in self.assets if a and a.strip()]
        if not cleaned:
            msg = "Select at least one asset to rescan."
            raise ValueError(msg)
        self.assets = list(dict.fromkeys(cleaned))
        return self


class RescanDimension(BaseModel):
    dimension: str
    label: str
    noun: str
    noun_plural: str
    seed_kind: str
    default_stages: list[str]


class RescanSchema(BaseModel):
    dimensions: list[RescanDimension]
    rescannable_stages: list[str]
    max_assets: int


class ScanBatchCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    engine_id: uuid.UUID | None = None
    context_id: uuid.UUID | None = None
    target_ids: list[uuid.UUID] = Field(default_factory=list, max_length=MAX_SCAN_BATCH)
    target_values: list[str] = Field(default_factory=list, max_length=MAX_SCAN_BATCH)
    overrides: dict[str, dict] = Field(default_factory=dict)
    intensity: str | None = None

    @model_validator(mode="after")
    def _require_targets(self):
        total = len(self.target_ids) + len(self.target_values)
        if total == 0:
            msg = "Select at least one target."
            raise ValueError(msg)
        if total > MAX_SCAN_BATCH:
            msg = f"Select at most {MAX_SCAN_BATCH} targets."
            raise ValueError(msg)
        return self


class ScanRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    target_id: uuid.UUID
    engine_id: uuid.UUID | None
    engine_name: str
    context_id: uuid.UUID | None
    context_name: str | None
    schedule_id: uuid.UUID | None = None
    schedule_type: str | None = None
    scope: str = ScanScope.FULL.value
    parent_scan_id: uuid.UUID | None = None
    seed_count: int = 0
    execution_config: ResolvedScanConfig
    auth_summary: str
    status: str
    subdomains_found: int
    ips_found: int
    open_ports_found: int
    http_assets_found: int
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
    new_subdomains: int = 0


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
