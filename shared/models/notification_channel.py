import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator
from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from shared.enums.notification import NotificationType
from shared.enums.notification_channel import NotificationProvider
from shared.utils.datetime import utc_now
from shared.utils.validation import clean_name

PROVIDERS = tuple(p.value for p in NotificationProvider)

DEFAULT_PREFERENCE_TYPES = [
    NotificationType.SCAN.value,
    NotificationType.VULNERABILITY.value,
    NotificationType.TARGET.value,
    NotificationType.SECURITY.value,
    NotificationType.SYSTEM.value,
]


class NotificationPreference(BaseModel):
    types: list[str] = Field(default_factory=lambda: list(DEFAULT_PREFERENCE_TYPES))
    min_severity: str = "info"


class NotificationChannel(SQLModel, table=True):
    __tablename__ = "notification_channels"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    name: str = Field(max_length=120)
    provider: str = Field(max_length=20)
    is_active: bool = Field(default=True)
    config_encrypted: str = Field(default="")
    events: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    created_by: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    last_test_at: datetime | None = Field(default=None)
    last_test_ok: bool | None = Field(default=None)
    last_test_message: str | None = Field(default=None)


class NotificationChannelCreate(BaseModel):
    name: str
    provider: str
    is_active: bool = True
    config: dict
    events: NotificationPreference = NotificationPreference()

    _validate_name = field_validator("name")(clean_name)


class NotificationChannelUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    config: dict | None = None
    events: NotificationPreference | None = None


class NotificationChannelRead(BaseModel):
    id: uuid.UUID
    name: str
    provider: str
    is_active: bool
    config_masked: dict
    events: NotificationPreference
    created_at: datetime
    updated_at: datetime
    last_test_at: datetime | None
    last_test_ok: bool | None
    last_test_message: str | None


class NotificationChannelTestConfig(BaseModel):
    provider: str
    config: dict


class NotificationChannelTestResult(BaseModel):
    success: bool
    message: str
