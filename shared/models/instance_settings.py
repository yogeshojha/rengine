import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel, UniqueConstraint

from shared.enums.instance import InstanceMode
from shared.utils.datetime import utc_now


class InstanceSettings(SQLModel, table=True):
    __tablename__ = "instance_settings"
    __table_args__ = (
        UniqueConstraint("singleton_key", name="uq_instance_settings_singleton"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    singleton_key: str = Field(default="instance", max_length=20)
    instance_name: str = Field(default="reNgine", max_length=120)
    timezone: str = Field(default="UTC", max_length=64)
    mode: str = Field(default=InstanceMode.BUG_BOUNTY.value)
    onboarding_completed: bool = Field(default=False)
    onboarding_completed_at: datetime | None = Field(default=None)
    onboarding_completed_by: uuid.UUID | None = Field(default=None)
    onboarding_step: int = Field(default=0)
    onboarding_state: dict = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    scan_history_retention_days: int = Field(default=90)
    screenshot_retention_days: int = Field(default=30)
    ai_enabled: bool = Field(default=False)
    ai_provider: str | None = Field(default=None)
    ai_model: str | None = Field(default=None)
    ai_api_key_encrypted: str | None = Field(default=None)
    ai_features: dict = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    report_defaults: dict = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class InstanceSettingsUpdate(BaseModel):
    instance_name: str | None = None
    timezone: str | None = None
    mode: str | None = None
    scan_history_retention_days: int | None = None
    screenshot_retention_days: int | None = None
    ai_enabled: bool | None = None
    ai_provider: str | None = None
    ai_model: str | None = None
    ai_api_key: str | None = None
    ai_features: dict | None = None


class InstanceSettingsRead(BaseModel):
    id: uuid.UUID
    singleton_key: str
    instance_name: str
    timezone: str
    mode: str
    onboarding_completed: bool
    onboarding_completed_at: datetime | None
    onboarding_completed_by: uuid.UUID | None
    onboarding_step: int
    onboarding_state: dict
    scan_history_retention_days: int
    screenshot_retention_days: int
    ai_enabled: bool
    ai_provider: str | None
    ai_model: str | None
    ai_api_key_masked: str | None
    ai_configured: bool
    ai_features: dict
    capabilities: list[str]
    created_at: datetime
    updated_at: datetime
