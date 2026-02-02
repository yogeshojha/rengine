from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, SQLModel
from sqlmodel import Field as SQLField

from app.enums.notification import NotificationSeverity, NotificationType

MAX_URL_LENGTH = 500


class NotificationMetadata(BaseModel):
    url: str | None = None
    open_new_tab: bool = False
    scan_id: str | None = None
    target_id: str | None = None
    action_label: str | None = Field(default=None, max_length=50)

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if (
            not v.startswith("/")
            and not v.startswith("http://")
            and not v.startswith("https://")
        ):
            msg = "URL must be relative (start with /) or absolute (http/https)"
            raise ValueError(msg)
        if len(v) > MAX_URL_LENGTH:
            msg = f"URL too long (max {MAX_URL_LENGTH} characters)"
            raise ValueError(msg)
        return v


class NotificationBase(SQLModel):
    type: NotificationType
    severity: NotificationSeverity
    title: str = SQLField(max_length=200)
    message: str = SQLField(sa_column=Column(Text))


class Notification(NotificationBase, table=True):
    __tablename__ = "notifications"
    __table_args__ = ({"sqlite_autoincrement": True},)

    id: int = SQLField(default=None, primary_key=True, index=True)
    notification_metadata: dict = SQLField(
        default_factory=dict, sa_column=Column(JSONB if True else Text)
    )
    is_read: bool = SQLField(default=False, index=True)
    created_at: datetime = SQLField(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None), index=True
    )
    expires_at: datetime = SQLField(
        default_factory=lambda: (datetime.now(UTC) + timedelta(days=7)).replace(
            tzinfo=None
        ),
        index=True,
    )


class NotificationCreate(NotificationBase):
    metadata: NotificationMetadata | None = None


class NotificationRead(NotificationBase):
    id: int
    notification_metadata: dict
    is_read: bool
    created_at: datetime
    expires_at: datetime


class NotificationMarkRead(BaseModel):
    notification_id: int


class NotificationStats(BaseModel):
    total: int
    unread: int
