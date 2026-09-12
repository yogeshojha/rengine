import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import Column, PrimaryKeyConstraint, UniqueConstraint
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from shared.definitions.watch import (
    DEFAULT_RATE_LIMIT,
    MAX_ALERT_QUERY,
    MAX_CHANNELS,
    MAX_RATE_LIMIT,
    WatchCadence,
    WatchStatus,
)
from shared.enums.scan import INTENSITIES
from shared.utils.datetime import utc_now
from shared.utils.text import strip_control


class ProgramWatch(SQLModel, table=True):
    __tablename__ = "program_watches"
    __table_args__ = (
        UniqueConstraint("project_id", "program_id", name="uq_program_watch"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)
    program_id: uuid.UUID = Field(
        foreign_key="bounty_programs.id", index=True, ondelete="CASCADE"
    )
    organization_id: uuid.UUID | None = Field(default=None)
    context_id: uuid.UUID | None = Field(default=None)
    schedule_id: uuid.UUID | None = Field(default=None)
    status: str = Field(default=WatchStatus.ACTIVE.value, max_length=16, index=True)

    engine_id: uuid.UUID | None = Field(default=None)
    cadence: str = Field(default=WatchCadence.WEEKLY.value, max_length=16)
    intensity: str | None = Field(default=None, max_length=16)
    rate_limit: int | None = Field(default=DEFAULT_RATE_LIMIT)
    probe_on_resolve: bool = Field(default=True)
    probe_engine_id: uuid.UUID | None = Field(default=None)
    follow_scope: bool = Field(default=True)
    alert_unresolved: bool = Field(default=False)
    alert_query: str = Field(default="", max_length=MAX_ALERT_QUERY)
    channel_ids: list = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    notify_in_app: bool = Field(default=True)

    watch_items: list = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    unenforceable: list = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    hosts_seen: int = Field(default=0)
    hosts_alerted: int = Field(default=0)
    last_certificate_at: datetime | None = Field(default=None)
    last_alert_at: datetime | None = Field(default=None)
    last_error: str | None = Field(default=None, max_length=500)

    created_by: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class WatchHost(SQLModel, table=True):
    __tablename__ = "watch_hosts"
    __table_args__ = (UniqueConstraint("watch_id", "name", name="uq_watch_host"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    watch_id: uuid.UUID = Field(
        foreign_key="program_watches.id", index=True, ondelete="CASCADE"
    )
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)
    target_id: uuid.UUID = Field(
        foreign_key="targets.id", index=True, ondelete="CASCADE"
    )
    name: str = Field(max_length=500, index=True)
    state: str = Field(max_length=16, index=True)
    reason: str | None = Field(default=None, max_length=200)
    matched_item: str | None = Field(default=None, max_length=500)

    cert_sha256: str | None = Field(default=None, max_length=64)
    issuer: str | None = Field(default=None, max_length=500)
    not_before: datetime | None = Field(default=None)
    sightings: int = Field(default=1)
    first_seen_at: datetime = Field(default_factory=utc_now, index=True)
    last_seen_at: datetime = Field(default_factory=utc_now)

    resolved_ips: list = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    cname: str | None = Field(default=None, max_length=500)
    is_wildcard: bool = Field(default=False)
    resolved_at: datetime | None = Field(default=None)
    next_check_at: datetime | None = Field(default=None, index=True)

    scan_id: uuid.UUID | None = Field(default=None, index=True)
    probed_at: datetime | None = Field(default=None)
    status_code: int | None = Field(default=None)
    title: str | None = Field(default=None, max_length=1000)
    tech: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    screenshot_path: str | None = Field(default=None, max_length=500)
    fingerprint: str | None = Field(default=None, max_length=64)
    alerted_at: datetime | None = Field(default=None)
    alerts: int = Field(default=0)
    muted_from: str | None = Field(default=None, max_length=16)


class WatchEvent(SQLModel, table=True):
    __tablename__ = "watch_events"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    watch_id: uuid.UUID = Field(
        foreign_key="program_watches.id", index=True, ondelete="CASCADE"
    )
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)
    kind: str = Field(max_length=32, index=True)
    name: str | None = Field(default=None, max_length=500)
    detail: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=utc_now, index=True)


class UserMark(SQLModel, table=True):
    __tablename__ = "user_marks"
    __table_args__ = (PrimaryKeyConstraint("user_id", "key"),)

    user_id: uuid.UUID = Field(foreign_key="users.id", ondelete="CASCADE")
    key: str = Field(max_length=120)
    marked_at: datetime = Field(default_factory=utc_now)


# ---------- schemas ----------


def _clean_query(v: str) -> str:
    return strip_control(v or "").strip()[:MAX_ALERT_QUERY]


class WatchSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    engine_id: uuid.UUID | None = None
    cadence: str = WatchCadence.WEEKLY.value
    intensity: str | None = None
    rate_limit: int | None = DEFAULT_RATE_LIMIT
    probe_on_resolve: bool = True
    probe_engine_id: uuid.UUID | None = None
    follow_scope: bool = True
    alert_unresolved: bool = False
    alert_query: str = ""
    channel_ids: list[uuid.UUID] = Field(default_factory=list, max_length=MAX_CHANNELS)
    notify_in_app: bool = True

    _clean_query = field_validator("alert_query")(_clean_query)

    @field_validator("cadence")
    @classmethod
    def _cadence(cls, v: str) -> str:
        if v not in {c.value for c in WatchCadence}:
            msg = "Unknown cadence."
            raise ValueError(msg)
        return v

    @field_validator("intensity")
    @classmethod
    def _intensity(cls, v: str | None) -> str | None:
        if v is not None and v not in INTENSITIES:
            msg = "Unknown intensity."
            raise ValueError(msg)
        return v

    @field_validator("rate_limit")
    @classmethod
    def _rate(cls, v: int | None) -> int | None:
        if v is not None and not 1 <= v <= MAX_RATE_LIMIT:
            msg = f"Rate ceiling must be between 1 and {MAX_RATE_LIMIT}."
            raise ValueError(msg)
        return v


class WatchCreate(WatchSettings):
    project_id: uuid.UUID
    run_baseline_now: bool = True


class WatchUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str | None = None
    engine_id: uuid.UUID | None = None
    cadence: str | None = None
    intensity: str | None = None
    rate_limit: int | None = None
    probe_on_resolve: bool | None = None
    probe_engine_id: uuid.UUID | None = None
    follow_scope: bool | None = None
    alert_unresolved: bool | None = None
    alert_query: str | None = None
    channel_ids: list[uuid.UUID] | None = Field(default=None, max_length=MAX_CHANNELS)
    notify_in_app: bool | None = None

    @field_validator("status")
    @classmethod
    def _status(cls, v: str | None) -> str | None:
        if v is not None and v not in {s.value for s in WatchStatus}:
            msg = "Unknown status."
            raise ValueError(msg)
        return v

    @field_validator("alert_query")
    @classmethod
    def _query(cls, v: str | None) -> str | None:
        return None if v is None else _clean_query(v)

    @field_validator("cadence")
    @classmethod
    def _cadence(cls, v: str | None) -> str | None:
        if v is not None and v not in {c.value for c in WatchCadence}:
            msg = "Unknown cadence."
            raise ValueError(msg)
        return v

    @field_validator("intensity")
    @classmethod
    def _intensity(cls, v: str | None) -> str | None:
        if v is not None and v not in INTENSITIES:
            msg = "Unknown intensity."
            raise ValueError(msg)
        return v

    @field_validator("rate_limit")
    @classmethod
    def _rate(cls, v: int | None) -> int | None:
        if v is not None and not 1 <= v <= MAX_RATE_LIMIT:
            msg = f"Rate ceiling must be between 1 and {MAX_RATE_LIMIT}."
            raise ValueError(msg)
        return v


class WatchTargetPreview(BaseModel):
    value: str
    type: str
    exists: bool
    watched: bool


class WatchPreview(BaseModel):
    targets: list[WatchTargetPreview]
    wildcards: int
    domains: int
    items: list[str]
    items_total: int = 0
    excluded_hosts: int
    excluded_ips: int
    unenforceable: list[str]
    existing: bool


class WatchBaseline(BaseModel):
    schedule_id: uuid.UUID | None = None
    engine_name: str | None = None
    status: str | None = None
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None
    running: int = 0


class WatchRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    program_id: uuid.UUID
    platform: str
    handle: str
    program_name: str
    profile_picture: str | None = None
    submission_state: str = "unknown"
    status: str
    organization_id: uuid.UUID | None
    context_id: uuid.UUID | None
    engine_id: uuid.UUID | None
    cadence: str
    intensity: str | None
    rate_limit: int | None
    probe_on_resolve: bool
    probe_engine_id: uuid.UUID | None
    follow_scope: bool
    alert_unresolved: bool
    alert_query: str
    channel_ids: list[uuid.UUID]
    notify_in_app: bool
    watch_items: list[str]
    items_total: int = 0
    unenforceable: list[str]
    targets: int = 0
    hosts_seen: int
    hosts_alerted: int
    last_certificate_at: datetime | None
    last_alert_at: datetime | None
    last_error: str | None
    baseline: WatchBaseline
    seen_at: datetime | None = None
    new_hosts: int = 0
    new_alerts: int = 0
    scope_changes: int = 0
    created_at: datetime
    updated_at: datetime


class WatchHostRead(BaseModel):
    id: uuid.UUID
    watch_id: uuid.UUID
    target_id: uuid.UUID
    name: str
    state: str
    state_label: str
    reason: str | None
    matched_item: str | None
    issuer: str | None
    not_before: datetime | None
    sightings: int
    first_seen_at: datetime
    last_seen_at: datetime
    resolved_ips: list[str]
    cname: str | None
    is_wildcard: bool
    scan_id: uuid.UUID | None
    probed_at: datetime | None
    status_code: int | None
    title: str | None
    tech: list[str]
    screenshot_path: str | None
    alerted_at: datetime | None
    alerts: int


class WatchEventRead(BaseModel):
    id: uuid.UUID
    watch_id: uuid.UUID
    kind: str
    label: str
    name: str | None
    detail: str | None
    created_at: datetime


class WatchHostCounts(BaseModel):
    all: int = 0
    arrived: int = 0
    alerted: int = 0
    unresolved: int = 0
    known: int = 0
    out_of_scope: int = 0


class StreamStatus(BaseModel):
    running: bool = False
    reachable: bool = False
    items: int = 0
    started_at: datetime | None = None
    updated_at: datetime | None = None
    last_certificate_at: datetime | None = None
    certificates_seen: int = 0
    last_error: str | None = None
    last_error_at: datetime | None = None
    version: str | None = None
