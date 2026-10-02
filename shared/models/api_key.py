import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel, UniqueConstraint

from shared.enums.api_key import APIProvider
from shared.utils.datetime import utc_now


class APIKey(SQLModel, table=True):
    __tablename__ = "api_keys"
    __table_args__ = (UniqueConstraint("provider", name="uq_api_key_provider"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    provider: APIProvider = Field(index=True)
    key_value: str = Field(max_length=1000)
    key_meta: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    is_enabled: bool = Field(default=True)
    usage_counter: int = Field(default=0)
    last_used_at: datetime | None = Field(default=None)
    last_test_at: datetime | None = Field(default=None)
    last_test_ok: bool | None = Field(default=None)
    last_test_message: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class APIKeyCreate(BaseModel):
    provider: APIProvider
    key_value: str
    key_meta: dict | None = None


class APIKeyUpdate(BaseModel):
    key_value: str | None = None
    is_enabled: bool | None = None
    key_meta: dict | None = None


class APIKeyRead(BaseModel):
    id: uuid.UUID
    provider: APIProvider
    key_value_masked: str
    key_meta: dict | None = None
    is_enabled: bool
    last_test_at: datetime | None = None
    last_test_ok: bool | None = None
    last_test_message: str | None = None
    created_at: datetime
    updated_at: datetime


class ProviderInfo(BaseModel):
    provider: APIProvider
    name: str
    description: str
    docs_url: str
    icon: str = "package"
    requires_username: bool = False
    group: str
    group_label: str
    configured: bool = False
    is_enabled: bool = False
    testable: bool = False
