import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField
from sqlalchemy import Column, Index, Text
from sqlmodel import Field, SQLModel, UniqueConstraint

from shared.utils.datetime import utc_now


class AiNarrative(SQLModel, table=True):
    """Written prose keyed by what it was written from."""

    __tablename__ = "ai_narratives"
    __table_args__ = (
        UniqueConstraint("task", "cache_key", name="uq_ai_narrative_task_key"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    task: str = Field(max_length=40, index=True)
    cache_key: str = Field(max_length=64, index=True)
    subject: str = Field(default="", max_length=300)
    provider: str = Field(max_length=32)
    model: str = Field(max_length=80)
    content: str = Field(sa_column=Column(Text, nullable=False))
    input_tokens: int = Field(default=0)
    output_tokens: int = Field(default=0)
    hits: int = Field(default=0)
    created_at: datetime = Field(default_factory=utc_now, index=True)
    last_used_at: datetime = Field(default_factory=utc_now)


class AiCall(SQLModel, table=True):
    __tablename__ = "ai_calls"
    __table_args__ = (Index("ix_ai_calls_feature_at", "feature", "at"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    at: datetime = Field(default_factory=utc_now, index=True)
    task: str = Field(max_length=40)
    feature: str = Field(max_length=40)
    provider: str = Field(max_length=32)
    model: str = Field(max_length=80)
    ok: bool = Field(default=True)
    cached: bool = Field(default=False)
    rounds: int = Field(default=1)
    input_tokens: int = Field(default=0)
    output_tokens: int = Field(default=0)
    cost_usd: float | None = Field(default=None)
    latency_ms: int = Field(default=0)
    error: str | None = Field(default=None, max_length=300)
    source_kind: str | None = Field(default=None, max_length=20)
    source_id: uuid.UUID | None = Field(default=None)
    user_id: uuid.UUID | None = Field(default=None)


class AiCallRead(BaseModel):
    id: uuid.UUID
    at: datetime
    task: str
    feature: str
    provider: str
    model: str
    ok: bool
    cached: bool
    rounds: int
    input_tokens: int
    output_tokens: int
    cost_usd: float | None
    latency_ms: int
    error: str | None
    source_kind: str | None
    source_id: uuid.UUID | None


class AiFeatureUsage(BaseModel):
    feature: str
    label: str
    calls: int = 0
    cached: int = 0
    failed: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float | None = None
    last_at: datetime | None = None


class AskUsageRead(BaseModel):
    questions: int = 0
    threads: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float | None = None
    since: datetime | None = None


class AiUsageRead(BaseModel):
    calls: int = 0
    cached: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float | None = None
    reports: int = 0
    failed: int = 0
    since: datetime | None = None
    ask: AskUsageRead = AskUsageRead()
    by_feature: list[AiFeatureUsage] = []


class AiStatus(BaseModel):
    """AI connection status with the key masked."""

    enabled: bool = False
    configured: bool = False
    provider: str | None = None
    model: str | None = None
    fast_model: str | None = None
    workspace_id: str | None = None
    base_url: str | None = None
    key_masked: str | None = None
    features: dict[str, bool] = PydanticField(default_factory=dict)
    usage: AiUsageRead = PydanticField(default_factory=AiUsageRead)
    cached_narratives: int = 0


class AiSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    provider: str | None = PydanticField(default=None, max_length=32)
    model: str | None = PydanticField(default=None, max_length=80)
    fast_model: str | None = PydanticField(default=None, max_length=80)
    workspace_id: str | None = PydanticField(default=None, max_length=80)
    base_url: str | None = PydanticField(default=None, max_length=300)
    api_key: str | None = PydanticField(default=None, max_length=400)
    features: dict[str, bool] | None = None


class AiTestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str | None = PydanticField(default=None, max_length=32)
    model: str | None = PydanticField(default=None, max_length=80)
    workspace_id: str | None = PydanticField(default=None, max_length=80)
    base_url: str | None = PydanticField(default=None, max_length=300)
    api_key: str | None = PydanticField(default=None, max_length=400)


class AiTestResult(BaseModel):
    success: bool
    message: str
    model: str | None = None
    latency_ms: int | None = None
