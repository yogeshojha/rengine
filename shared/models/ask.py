"""Ask threads: one user, a read-only conversation on the estate or one asset."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator
from pydantic import Field as PField
from sqlalchemy import Column, Index, Text
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from shared.definitions.ask import (
    ASK_DIMENSIONS,
    MAX_BLOCK_QUERY,
    MAX_BLOCK_TITLE,
    MAX_QUESTION_CHARS,
    MAX_TITLE,
    AskSubject,
    MessageRole,
)
from shared.definitions.notes import MAX_ASSET_KEY
from shared.definitions.surface import SurfaceDimension
from shared.utils.datetime import utc_now
from shared.utils.text import strip_control


class Fact(BaseModel):
    n: int
    tone: str
    label: str
    detail: str | None = None
    field: str | None = None
    lines: list[int] = []


class Citation(BaseModel):
    n: int
    kind: str
    label: str
    detail: str | None = None
    field: str | None = None
    lines: list[int] = []
    pivot: str | None = None


class TraceStep(BaseModel):
    tool: str
    label: str
    status: str
    rows: int | None = None
    pivot: str | None = None
    ms: int = 0
    detail: str | None = None
    args: str | None = None


class Suggestion(BaseModel):
    decision: str
    next: str


class AskFlagRead(BaseModel):
    kind: str
    field: str
    line: int
    sample: str


class AskBrief(BaseModel):
    verdict: str
    label: str
    facts: list[Fact]
    available: bool
    off_reason: str | None = None
    model: str | None = None
    starters: list[str] = []


class AskThread(SQLModel, table=True):
    __tablename__ = "ask_threads"
    __table_args__ = (
        Index("ix_ask_threads_asset", "target_id", "dimension", "asset_key", "user_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(
        foreign_key="projects.id", index=True, ondelete="CASCADE"
    )
    subject: str = Field(default=AskSubject.ASSET.value, max_length=16)
    target_id: uuid.UUID | None = Field(
        default=None, foreign_key="targets.id", index=True, ondelete="CASCADE"
    )
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True, ondelete="CASCADE")
    dimension: str = Field(
        default=SurfaceDimension.VULNERABILITIES.value, max_length=32
    )
    asset_key: str | None = Field(default=None, max_length=MAX_ASSET_KEY)
    # the estate a thread asks about: target ids, organization and tag
    scope: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    title: str | None = Field(default=None, max_length=MAX_TITLE)
    message_count: int = Field(default=0)
    input_tokens: int = Field(default=0)
    output_tokens: int = Field(default=0)
    cost_usd: float | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)
    last_at: datetime = Field(default_factory=utc_now)


class AskMessage(SQLModel, table=True):
    __tablename__ = "ask_messages"
    __table_args__ = (
        Index("ix_ask_messages_thread_created", "thread_id", "created_at"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    thread_id: uuid.UUID = Field(
        foreign_key="ask_threads.id", index=True, ondelete="CASCADE"
    )
    role: str = Field(default=MessageRole.USER.value, max_length=16)
    text: str = Field(sa_column=Column(Text, nullable=False))
    citations: list = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    trace: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    flags: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    suggestion: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    blocks: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    follow_ups: list = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    about: str | None = Field(default=None, max_length=MAX_ASSET_KEY)
    intelligent: bool = Field(default=False)
    model: str | None = Field(default=None, max_length=80)
    input_tokens: int = Field(default=0)
    output_tokens: int = Field(default=0)
    cost_usd: float | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)


class AskThreadCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: uuid.UUID
    dimension: str = PField(
        default=SurfaceDimension.VULNERABILITIES.value, max_length=32
    )
    asset_key: str = PField(min_length=1, max_length=MAX_ASSET_KEY)
    title: str | None = PField(default=None, max_length=MAX_TITLE)

    @field_validator("dimension")
    @classmethod
    def _known(cls, value: str) -> str:
        if value not in ASK_DIMENSIONS:
            msg = "Ask is not offered on that dimension."
            raise ValueError(msg)
        return value


class AskQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = PField(min_length=1, max_length=MAX_QUESTION_CHARS)
    scan_id: uuid.UUID

    @field_validator("text")
    @classmethod
    def _clean(cls, value: str) -> str:
        cleaned = strip_control(value).strip()
        if not cleaned:
            msg = "Question is empty."
            raise ValueError(msg)
        return cleaned


class AskThreadRead(BaseModel):
    id: uuid.UUID
    target_id: uuid.UUID
    dimension: str
    asset_key: str
    title: str
    message_count: int
    cost_usd: float | None = None
    created_at: datetime
    last_at: datetime


class AnswerBlock(BaseModel):
    """The query and count behind a block."""

    id: str
    kind: str
    dimension: str | None = None
    query: str | None = None
    group_by: str | None = None
    cve: str | None = None
    title: str | None = None
    total: int | None = None
    capped: bool = False
    about: str | None = None
    edited: bool = False
    cause_key: str | None = None


class FollowUp(BaseModel):
    text: str
    source: str
    reason: str | None = None
    dimension: str | None = None
    query: str | None = None
    title: str | None = None
    count: int | None = None
    capped: bool = False
    about: str | None = None


class AskMessageRead(BaseModel):
    id: uuid.UUID
    role: str
    text: str
    citations: list[Citation] = []
    trace: list[TraceStep] = []
    flags: list[AskFlagRead] = []
    suggestion: Suggestion | None = None
    blocks: list[AnswerBlock] = []
    follow_ups: list[FollowUp] = []
    about: str | None = None
    intelligent: bool = False
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float | None = None
    created_at: datetime


class AskThreadDetail(BaseModel):
    thread: AskThreadRead
    messages: list[AskMessageRead]


# ---------- the estate ----------


class EstateScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_ids: list[uuid.UUID] = PField(default_factory=list, max_length=500)
    organization_id: uuid.UUID | None = None
    tag_id: uuid.UUID | None = None
    scan_id: uuid.UUID | None = None


class EstateThreadCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: EstateScope = PField(default_factory=EstateScope)
    title: str | None = PField(default=None, max_length=MAX_TITLE)


class EstateScopeRead(BaseModel):
    target_ids: list[uuid.UUID] = []
    organization_id: uuid.UUID | None = None
    tag_id: uuid.UUID | None = None
    scan_id: uuid.UUID | None = None
    scan_at: datetime | None = None
    scan_target: str | None = None
    label: str
    targets: int
    filtered: bool = False
    links: list[str] = []


class EstateThreadRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    scope: EstateScopeRead
    message_count: int
    cost_usd: float | None = None
    created_at: datetime
    last_at: datetime


class EstateThreadDetail(BaseModel):
    thread: EstateThreadRead
    messages: list[AskMessageRead]


class PinnedQuery(BaseModel):
    """A block the server shows before the model answers."""

    model_config = ConfigDict(extra="forbid")

    dimension: str = PField(min_length=1, max_length=40)
    query: str | None = PField(default=None, max_length=MAX_BLOCK_QUERY)
    title: str | None = PField(default=None, max_length=MAX_BLOCK_TITLE * 20)

    @field_validator("title")
    @classmethod
    def _title(cls, value: str | None) -> str | None:
        cleaned = " ".join(strip_control(value or "").split())
        return cleaned[:MAX_BLOCK_TITLE] or None


class EstateQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = PField(min_length=1, max_length=MAX_QUESTION_CHARS)
    # a block id, or a row a person pointed at as dimension:value
    about: str | None = PField(default=None, max_length=MAX_ASSET_KEY)
    intelligent: bool = False
    pinned: PinnedQuery | None = None

    @field_validator("text")
    @classmethod
    def _clean(cls, value: str) -> str:
        cleaned = strip_control(value).strip()
        if not cleaned:
            msg = "Question is empty."
            raise ValueError(msg)
        return cleaned

    @field_validator("about")
    @classmethod
    def _about(cls, value: str | None) -> str | None:
        cleaned = strip_control(value or "").strip()
        return cleaned or None


class BlockGroup(BaseModel):
    value: str
    label: str
    count: int
    query: str | None = None


class BlockCauseDetail(BaseModel):
    label: str
    count: int
    hint: str | None = None


class BlockCause(BaseModel):
    value: str
    label: str
    count: int
    query: str | None = None
    who: str | None = None
    details: list[BlockCauseDetail] = []


class BlockCauses(BaseModel):
    """The groups that concentrate a block's rows."""

    key: str
    one: str
    many: str
    prep: str = "on"
    mono: bool = False
    address: bool = False
    total_groups: int
    groups: list[BlockCause] = []


class BlockFactRead(BaseModel):
    title: str
    question: str
    query: str
    count: int
    capped: bool = False


class ReadToken(BaseModel):
    """One clause of a block's query, as a person reads it."""

    kind: str
    text: str
    field: str | None = None
    op: str | None = None
    negated: bool = False
    hint: str | None = None


class BlockData(BaseModel):
    """What a block shows now, read from its stored query."""

    id: str
    kind: str
    dimension: str | None = None
    total: int | None = None
    capped: bool = False
    rows: list[dict] = []
    groups: list[BlockGroup] = []
    covered: int | None = None
    record: dict | None = None
    scope_values: list[str] = []
    error: str | None = None
    causes: BlockCauses | None = None
    facts: list[BlockFactRead] = []
    reading: list[ReadToken] = []
    scope_total: int | None = None
    scope_capped: bool = False


class BlockQueryEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = PField(min_length=1, max_length=MAX_BLOCK_QUERY)

    @field_validator("query")
    @classmethod
    def _clean(cls, value: str) -> str:
        cleaned = strip_control(value).strip()
        if not cleaned:
            msg = "Query is empty."
            raise ValueError(msg)
        return cleaned


class StarterCause(BaseModel):
    key: str
    value: str
    label: str
    count: int
    one: str


class EstateStarterRead(BaseModel):
    key: str
    question: str
    statement: str
    dimension: str
    query: str
    count: int
    capped: bool = False
    cause: StarterCause | None = None


class EstateStarters(BaseModel):
    filtered: bool
    scope_values: list[str] = []
    starters: list[EstateStarterRead] = []
    example: str | None = None


class EstateScanOption(BaseModel):
    id: uuid.UUID
    target: str
    engine: str
    status: str
    scope: str
    at: datetime | None = None


class EstateStatus(BaseModel):
    available: bool
    off_reason: str | None = None
    off_code: str | None = None
    provider: str | None = None
    model: str | None = None
