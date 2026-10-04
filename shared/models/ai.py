import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField
from sqlalchemy import Column, Index, Text
from sqlmodel import Field, SQLModel, UniqueConstraint

from shared.definitions.ai import (
    MAX_API_KEY,
    MAX_BASE_URL,
    MAX_CATALOG_ID,
    MAX_CONNECTION_NAME,
    MAX_COST_SOURCE,
    MAX_MODEL_ID,
    MAX_PROVIDER,
    MAX_TEST_MESSAGE,
    MAX_WORKSPACE_ID,
)
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
    cache_read_tokens: int = Field(default=0)
    cache_write_tokens: int = Field(default=0)
    cost_usd: float | None = Field(default=None)
    cost_source: str | None = Field(default=None, max_length=MAX_COST_SOURCE)
    input_per_mtok: float | None = Field(default=None)
    output_per_mtok: float | None = Field(default=None)
    latency_ms: int = Field(default=0)
    error: str | None = Field(default=None, max_length=300)
    source_kind: str | None = Field(default=None, max_length=20)
    source_id: uuid.UUID | None = Field(default=None)
    user_id: uuid.UUID | None = Field(default=None)


class AiConnection(SQLModel, table=True):
    """A saved provider: its key, server and models."""

    __tablename__ = "ai_connections"
    __table_args__ = (UniqueConstraint("name", name="uq_ai_connection_name"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=MAX_CONNECTION_NAME)
    provider: str = Field(max_length=MAX_PROVIDER)
    api_key_encrypted: str | None = Field(default=None)
    base_url: str | None = Field(default=None, max_length=MAX_BASE_URL)
    model: str = Field(max_length=MAX_MODEL_ID)
    input_per_mtok: float | None = Field(default=None)
    output_per_mtok: float | None = Field(default=None)
    cache_read_per_mtok: float | None = Field(default=None)
    cache_write_per_mtok: float | None = Field(default=None)
    workspace_id: str | None = Field(default=None, max_length=MAX_WORKSPACE_ID)
    last_test_at: datetime | None = Field(default=None)
    last_test_ok: bool | None = Field(default=None)
    last_test_message: str | None = Field(default=None, max_length=MAX_TEST_MESSAGE)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AiPrice(SQLModel, table=True):
    """One model's list price, from the downloaded price list."""

    __tablename__ = "ai_prices"

    model_id: str = Field(primary_key=True, max_length=MAX_CATALOG_ID)
    input_per_mtok: float
    output_per_mtok: float
    cache_read_per_mtok: float | None = Field(default=None)
    cache_write_per_mtok: float | None = Field(default=None)


class AiConnectionRead(BaseModel):
    id: uuid.UUID
    name: str
    provider: str
    model: str
    base_url: str | None = None
    workspace_id: str | None = None
    key_masked: str | None = None
    in_use: bool = False
    last_test_at: datetime | None = None
    last_test_ok: bool | None = None
    last_test_message: str | None = None


class AiConnectionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = PydanticField(default=None, max_length=MAX_CONNECTION_NAME)
    provider: str = PydanticField(max_length=MAX_PROVIDER)
    api_key: str | None = PydanticField(default=None, max_length=MAX_API_KEY)
    base_url: str | None = PydanticField(default=None, max_length=MAX_BASE_URL)
    model: str | None = PydanticField(default=None, max_length=MAX_MODEL_ID)
    workspace_id: str | None = PydanticField(default=None, max_length=MAX_WORKSPACE_ID)
    use: bool = False


class AiConnectionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = PydanticField(default=None, max_length=MAX_CONNECTION_NAME)
    provider: str | None = PydanticField(default=None, max_length=MAX_PROVIDER)
    api_key: str | None = PydanticField(default=None, max_length=MAX_API_KEY)
    base_url: str | None = PydanticField(default=None, max_length=MAX_BASE_URL)
    model: str | None = PydanticField(default=None, max_length=MAX_MODEL_ID)
    workspace_id: str | None = PydanticField(default=None, max_length=MAX_WORKSPACE_ID)


class AiModelsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connection_id: uuid.UUID | None = None
    provider: str | None = PydanticField(default=None, max_length=MAX_PROVIDER)
    api_key: str | None = PydanticField(default=None, max_length=MAX_API_KEY)
    base_url: str | None = PydanticField(default=None, max_length=MAX_BASE_URL)
    workspace_id: str | None = PydanticField(default=None, max_length=MAX_WORKSPACE_ID)


class AiModelOption(BaseModel):
    id: str
    label: str
    input_per_mtok: float | None = None
    output_per_mtok: float | None = None
    cache_read_per_mtok: float | None = None
    cache_write_per_mtok: float | None = None
    recommended: bool = False


class AiModelList(BaseModel):
    models: list[AiModelOption] = PydanticField(default_factory=list)
    error: str | None = None


class AiOnboarding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    provider: str | None = PydanticField(default=None, max_length=MAX_PROVIDER)
    api_key: str | None = PydanticField(default=None, max_length=MAX_API_KEY)
    base_url: str | None = PydanticField(default=None, max_length=MAX_BASE_URL)
    workspace_id: str | None = PydanticField(default=None, max_length=MAX_WORKSPACE_ID)
    model: str | None = PydanticField(default=None, max_length=MAX_MODEL_ID)
    features: dict[str, bool] | None = None


class AiOnboardingRead(BaseModel):
    enabled: bool
    connection: AiConnectionRead | None = None
    features: dict[str, bool] = PydanticField(default_factory=dict)


class AiCallRead(BaseModel):
    id: uuid.UUID
    at: datetime
    feature: str
    provider: str
    model: str
    ok: bool
    cached: bool
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost_usd: float | None
    cost_source: str | None = None
    input_per_mtok: float | None = None
    output_per_mtok: float | None = None
    latency_ms: int
    error: str | None


class AiCallPage(BaseModel):
    items: list[AiCallRead] = PydanticField(default_factory=list)
    has_more: bool = False


class AiFeatureUsage(BaseModel):
    feature: str
    label: str
    calls: int = 0
    cached: int = 0
    failed: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost_usd: float | None = None
    unpriced: int = 0
    last_at: datetime | None = None


class AiUsageRead(BaseModel):
    calls: int = 0
    cost_usd: float | None = None
    unpriced: int = 0
    failed: int = 0
    since: datetime | None = None
    by_feature: list[AiFeatureUsage] = []


class AiStatus(BaseModel):
    """The provider in use, with the key masked."""

    enabled: bool = False
    configured: bool = False
    connection_id: uuid.UUID | None = None
    provider: str | None = None
    model: str | None = None
    workspace_id: str | None = None
    base_url: str | None = None
    key_masked: str | None = None
    features: dict[str, bool] = PydanticField(default_factory=dict)
    usage: AiUsageRead = PydanticField(default_factory=AiUsageRead)
    cached_narratives: int = 0


class AiSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    features: dict[str, bool] | None = None


class AiTestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connection_id: uuid.UUID | None = None
    provider: str | None = PydanticField(default=None, max_length=MAX_PROVIDER)
    model: str | None = PydanticField(default=None, max_length=MAX_MODEL_ID)
    workspace_id: str | None = PydanticField(default=None, max_length=MAX_WORKSPACE_ID)
    base_url: str | None = PydanticField(default=None, max_length=MAX_BASE_URL)
    api_key: str | None = PydanticField(default=None, max_length=MAX_API_KEY)


class AiTestResult(BaseModel):
    success: bool
    message: str
    model: str | None = None
    latency_ms: int | None = None
