"""Ask threads: one finding, one user, a read-only conversation."""

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
    MAX_QUESTION_CHARS,
    MAX_TITLE,
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
    masked: int = 0
    flags: list[AskFlagRead] = []
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
    target_id: uuid.UUID = Field(
        foreign_key="targets.id", index=True, ondelete="CASCADE"
    )
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True, ondelete="CASCADE")
    dimension: str = Field(
        default=SurfaceDimension.VULNERABILITIES.value, max_length=32
    )
    asset_key: str = Field(max_length=MAX_ASSET_KEY)
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


class AskMessageRead(BaseModel):
    id: uuid.UUID
    role: str
    text: str
    citations: list[Citation] = []
    trace: list[TraceStep] = []
    flags: list[AskFlagRead] = []
    suggestion: Suggestion | None = None
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float | None = None
    created_at: datetime


class AskThreadDetail(BaseModel):
    thread: AskThreadRead
    messages: list[AskMessageRead]
