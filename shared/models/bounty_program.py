import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column, Text
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel, UniqueConstraint

from shared.enums.target import TargetType
from shared.models.organization import OrganizationSummary
from shared.models.tag import TagSummary
from shared.utils.datetime import utc_now


class BountyProgram(SQLModel, table=True):
    __tablename__ = "bounty_programs"
    __table_args__ = (
        UniqueConstraint("platform", "handle", name="uq_bounty_program_handle"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    platform: str = Field(max_length=32, index=True)
    source: str = Field(default="api", max_length=16, index=True)
    handle: str = Field(max_length=200, index=True)
    name: str = Field(max_length=300)
    url: str | None = Field(default=None, max_length=500)
    profile_picture: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    program_state: str = Field(max_length=16, index=True)
    raw_state: str | None = Field(default=None, max_length=32)
    joined: bool = Field(default=False, index=True)
    joined_at: datetime | None = Field(default=None)
    submission_state: str = Field(max_length=16, index=True)
    offers_bounties: bool = Field(default=False, index=True)
    open_scope: bool | None = Field(default=None)
    gold_standard_safe_harbor: bool | None = Field(default=None)
    currency: str | None = Field(default=None, max_length=16)
    started_accepting_at: datetime | None = Field(default=None, index=True)
    bookmarked: bool = Field(default=False, index=True)
    reports_for_user: int | None = Field(default=None)
    earnings_for_user: float | None = Field(default=None)
    min_payout: float | None = Field(default=None)
    max_payout: float | None = Field(default=None)
    payout_currency: str | None = Field(default=None, max_length=16)
    safe_harbor: str | None = Field(default=None, max_length=32)
    requires_2fa: bool | None = Field(default=None)
    scopes_synced_at: datetime | None = Field(default=None)
    synced_at: datetime = Field(default_factory=utc_now, index=True)


class BountyScope(SQLModel, table=True):
    __tablename__ = "bounty_scopes"
    __table_args__ = (
        UniqueConstraint(
            "program_id", "asset_type", "asset_identifier", name="uq_bounty_scope_asset"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    program_id: uuid.UUID = Field(
        foreign_key="bounty_programs.id", index=True, ondelete="CASCADE"
    )
    asset_type: str = Field(max_length=48, index=True)
    asset_identifier: str = Field(max_length=1000)
    scope_state: str = Field(max_length=16, index=True)
    eligible_for_bounty: bool | None = Field(default=None)
    max_severity: str | None = Field(default=None, max_length=16)
    instruction: str | None = Field(default=None, sa_column=Column(Text))
    reference: str | None = Field(default=None, max_length=500)
    target_value: str | None = Field(default=None, max_length=500, index=True)
    target_type: TargetType | None = Field(default=None)
    raw: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    synced_at: datetime = Field(default_factory=utc_now)


class BountyEventRow(SQLModel, table=True):
    __tablename__ = "bounty_events"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    platform: str = Field(max_length=32, index=True)
    program_id: uuid.UUID = Field(
        foreign_key="bounty_programs.id", index=True, ondelete="CASCADE"
    )
    handle: str = Field(max_length=200, index=True)
    program_name: str = Field(max_length=300)
    kind: str = Field(max_length=32, index=True)
    asset_type: str | None = Field(default=None, max_length=48)
    asset_identifier: str | None = Field(default=None, max_length=1000)
    detail: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=utc_now, index=True)


class BountyEventRead(BaseModel):
    id: uuid.UUID
    platform: str
    handle: str
    program_name: str
    kind: str
    label: str = ""
    description: str = ""
    icon: str = "circle-help"
    tone: str = "muted"
    actionable: bool = False
    asset_type: str | None
    asset_identifier: str | None
    detail: str | None
    created_at: datetime


class BountyScopeRead(BaseModel):
    id: uuid.UUID
    asset_type: str
    asset_type_label: str
    asset_group: str
    icon: str
    asset_identifier: str
    scope_state: str
    eligible_for_bounty: bool | None
    max_severity: str | None
    instruction: str | None
    target_value: str | None
    target_type: str | None
    importable: bool
    already_target: bool = False


class BountyProgramRead(BaseModel):
    id: uuid.UUID
    platform: str
    platform_label: str = ""
    source: str = "api"
    source_label: str = ""
    handle: str
    name: str
    url: str | None
    profile_picture: str | None
    program_state: str
    raw_state: str | None
    raw_state_label: str = ""
    joined: bool
    joined_at: datetime | None
    submission_state: str
    offers_bounties: bool
    open_scope: bool | None
    gold_standard_safe_harbor: bool | None
    currency: str | None
    started_accepting_at: datetime | None
    bookmarked: bool
    reports_for_user: int | None
    earnings_for_user: float | None
    min_payout: float | None = None
    max_payout: float | None = None
    payout_currency: str | None = None
    safe_harbor: str | None = None
    requires_2fa: bool | None = None
    scopes_synced_at: datetime | None
    synced_at: datetime
    in_scope_count: int = 0
    out_of_scope_count: int = 0
    importable_count: int = 0
    imported_count: int = 0


class BountyProgramDetail(BountyProgramRead):
    scopes: list[BountyScopeRead] = []
    unreachable: dict[str, int] = {}


class BountyScopeCounts(BaseModel):
    total: int
    in_scope: int
    out_of_scope: int
    importable: int


class BountySyncResult(BaseModel):
    platform: str
    programs: int
    created: int
    updated: int
    duration_ms: int
    error: str | None = None


class BountyImportRequest(BaseModel):
    project_id: uuid.UUID
    scope_ids: list[uuid.UUID] | None = None
    include_out_of_scope: bool = False
    group_by_program: bool = True
    # blank falls back to the program name
    organization_name: str | None = None
    tags: list[str] = []


class BountyImportResult(BaseModel):
    created: list[str]
    existing: list[str]
    skipped: list[str]
    organization: OrganizationSummary | None = None
    tags: list[TagSummary] = []


class PlatformCount(BaseModel):
    platform: str
    label: str
    source: str
    programs: int


class BountyStatus(BaseModel):
    configured: bool
    platform: str
    username: str | None
    programs: int
    private_programs: int
    last_synced_at: datetime | None
    sync_interval: str
    next_sync_at: datetime | None = None
    unseen_events: int = 0
    platforms: list[PlatformCount] = []
    feed_interval: str = ""
    feed_synced_at: datetime | None = None
    error: str | None = None


class BountySettingsRead(BaseModel):
    sync_interval: str
    feed_interval: str
    feed_synced_at: datetime | None
    feed_next_sync_at: datetime | None
    feed_programs: int
    feed_source: str
    feed_url: str
    feed_license: str
    notify: bool
    notify_events: list[str]
    notifiable_events: list[str]
    last_synced_at: datetime | None
    next_sync_at: datetime | None
    programs: int
    events_recorded: int


class BountySettingsUpdate(BaseModel):
    sync_interval: str | None = None
    feed_interval: str | None = None
    notify: bool | None = None
    notify_events: list[str] | None = None
