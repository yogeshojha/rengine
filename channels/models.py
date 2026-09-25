"""Remote control persistence: one config row per channel, one row per paired chat."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField
from sqlalchemy import Column, UniqueConstraint
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

import shared.models._tztypes  # noqa: F401
from mcp.models import McpCeiling
from shared.definitions.channels import (
    MAX_DISPLAY,
    MAX_EXTERNAL_ID,
    ChatState,
)
from shared.utils.datetime import utc_now

MAX_CHANNEL = 16
MAX_COMMAND = 80


class ChannelConfig(SQLModel, table=True):
    __tablename__ = "channel_configs"

    channel: str = Field(primary_key=True, max_length=MAX_CHANNEL)
    enabled: bool = Field(default=False)
    settings: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    started_at: datetime | None = Field(default=None)
    updated_at: datetime = Field(default_factory=utc_now)
    updated_by: uuid.UUID | None = Field(default=None)


class ChannelChat(SQLModel, table=True):
    __tablename__ = "channel_chats"
    __table_args__ = (
        UniqueConstraint("channel", "external_id", name="uq_channel_chats_external"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    channel: str = Field(max_length=MAX_CHANNEL, index=True)
    external_id: str = Field(max_length=MAX_EXTERNAL_ID)
    display: str = Field(default="", max_length=MAX_DISPLAY)
    user_id: uuid.UUID | None = Field(
        default=None, foreign_key="users.id", index=True, ondelete="SET NULL"
    )
    project_id: uuid.UUID | None = Field(
        default=None, foreign_key="projects.id", index=True, ondelete="SET NULL"
    )
    capabilities: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    state: str = Field(default=ChatState.ACTIVE.value, max_length=16, index=True)
    approved_by: uuid.UUID | None = Field(default=None)
    approved_at: datetime | None = Field(default=None)
    revoked_at: datetime | None = Field(default=None)
    last_seen_at: datetime | None = Field(default=None)
    last_command: str | None = Field(default=None, max_length=MAX_COMMAND)
    calls: int = Field(default=0)
    created_at: datetime = Field(default_factory=utc_now)


# ---------- api shapes ----------


class BotInfo(BaseModel):
    id: str
    username: str
    name: str


class ListenerStatus(BaseModel):
    reporting: bool = False
    running: bool
    last_poll_at: datetime | None = None
    updates_seen: int = 0
    last_error: str | None = None
    last_error_at: datetime | None = None


class ChannelStatus(BaseModel):
    channel: str
    label: str
    configured: bool
    enabled: bool
    started_at: datetime | None
    secret_masked: str | None
    bot: BotInfo | None
    listener: ListenerStatus
    rate_limit_per_minute: int
    ceiling: dict[str, bool]
    capabilities: list[dict]
    chats_total: int
    chats_active: int
    pending_total: int
    commands_total: int
    calls_recent: int
    last_call_at: datetime | None
    shared_notifications: int = 0


class ChannelCatalogEntry(BaseModel):
    channel: str
    label: str
    configured: bool
    enabled: bool
    running: bool


class ChannelSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    rate_limit_per_minute: int | None = PydanticField(default=None, ge=1, le=10_000)
    ceiling: McpCeiling | None = None


class ChannelConnect(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = PydanticField(min_length=1, max_length=200)


class ChannelVerifyResult(BaseModel):
    ok: bool
    bot: BotInfo | None = None
    error: str | None = None


class PairingRequestRead(BaseModel):
    code: str
    external_id: str
    display: str
    username: str | None
    first_name: str | None
    requested_at: datetime
    expires_at: datetime


class PairingApprove(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: uuid.UUID
    project_id: uuid.UUID
    capabilities: list[str] = PydanticField(default_factory=list, max_length=8)


class ChannelChatRead(BaseModel):
    id: uuid.UUID
    channel: str
    external_id: str
    display: str
    user_id: uuid.UUID | None
    username: str | None
    totp_enabled: bool
    project_id: uuid.UUID | None
    project_name: str | None
    capabilities: list[str]
    effective_capabilities: list[str]
    state: str
    approved_at: datetime | None
    revoked_at: datetime | None
    last_seen_at: datetime | None
    last_command: str | None
    calls: int
    created_at: datetime


class ChannelChatUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: uuid.UUID | None = None
    capabilities: list[str] | None = PydanticField(default=None, max_length=8)


class CommandArgRead(BaseModel):
    name: str
    type: str
    required: bool
    description: str
    default: str | None = None
    options: list[str] = PydanticField(default_factory=list)


class ChannelCommandRead(BaseModel):
    name: str
    tool: str | None
    source: str
    group: str
    title: str
    description: str
    capability: str
    touches_target: bool
    queued: bool
    value_field: str
    presets: dict[str, object]
    usage: str
    args: list[CommandArgRead]
