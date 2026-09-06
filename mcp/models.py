"""MCP persistence: one table for service tokens, plus the API's read/write shapes."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField
from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

import shared.models._tztypes  # noqa: F401
from mcp.capabilities import Capability
from shared.utils.datetime import utc_now

MAX_NAME = 80
MAX_TOKENS = 50
EXPIRY_CHOICES: tuple[int | None, ...] = (7, 30, 90, 365, None)


class McpToken(SQLModel, table=True):
    __tablename__ = "mcp_tokens"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    name: str = Field(max_length=MAX_NAME, index=True)
    # null means every project this instance holds
    project_id: uuid.UUID | None = Field(default=None, index=True)
    capabilities: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    token_hash: str = Field(max_length=64, index=True, unique=True)
    token_prefix: str = Field(max_length=32)
    expires_at: datetime | None = Field(default=None)
    revoked_at: datetime | None = Field(default=None)
    last_used_at: datetime | None = Field(default=None)
    last_client: str | None = Field(default=None, max_length=120)
    calls: int = Field(default=0)
    created_by: uuid.UUID | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)


class McpTokenCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = PydanticField(min_length=1, max_length=MAX_NAME)
    project_id: uuid.UUID | None = None
    capabilities: list[str] = PydanticField(default_factory=list, max_length=8)
    expires_in_days: int | None = PydanticField(default=30, ge=1, le=365)


class McpTokenRead(BaseModel):
    id: uuid.UUID
    name: str
    project_id: uuid.UUID | None
    project_name: str | None = None
    capabilities: list[str]
    token_prefix: str
    expires_at: datetime | None
    expired: bool
    revoked: bool
    last_used_at: datetime | None
    last_client: str | None
    calls: int
    created_at: datetime


class McpTokenCreated(BaseModel):
    """The one time the secret is returned. reNgine stores only its hash."""

    token: McpTokenRead
    secret: str
    client_config: str


class McpCeiling(BaseModel):
    model_config = ConfigDict(extra="forbid")

    read: bool = True
    plan: bool = True
    write: bool = True
    launch: bool = False

    def as_dict(self) -> dict[str, bool]:
        return {
            Capability.READ.value: True,
            Capability.PLAN.value: self.plan,
            Capability.WRITE.value: self.write,
            Capability.LAUNCH.value: self.launch,
        }


class McpSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    rate_limit_per_minute: int | None = PydanticField(default=None, ge=1, le=10_000)
    ceiling: McpCeiling | None = None


class McpToolRead(BaseModel):
    name: str
    title: str
    description: str
    capability: str
    group: str
    destructive: bool = False
    examples: list[str]
    schema_: dict = PydanticField(default_factory=dict, alias="schema")

    model_config = ConfigDict(populate_by_name=True)


class McpSessionRead(BaseModel):
    token_id: uuid.UUID
    token_name: str
    client: str
    capabilities: list[str]
    first_seen: datetime
    last_seen: datetime
    calls: int
    last_tool: str | None = None


class McpCallRead(BaseModel):
    at: datetime
    token_name: str
    client: str
    tool: str
    ok: bool
    duration_ms: int
    detail: str | None = None


class McpStatus(BaseModel):
    enabled: bool
    started_at: datetime | None
    endpoint: str
    stdio_command: str
    protocol_version: str
    rate_limit_per_minute: int
    ceiling: dict[str, bool]
    tools_total: int
    tools_available: int
    tokens_total: int
    tokens_active: int
    sessions: list[McpSessionRead]
    calls_today: int
    last_call_at: datetime | None
    capabilities: list[dict]
