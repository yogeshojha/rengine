import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlmodel import Field, SQLModel

from shared.enums.activity import ActivityEvent, ActivityLevel
from shared.utils.datetime import utc_now


class ActivityLog(SQLModel, table=True):
    """Activity log for audit trails and live feed widgets.

    Scope is inferred from FK presence:
      - target_id set -> target-level event
      - project_id set (no target) -> project-level event
      - neither set -> system-level event
    """

    __tablename__ = "activity_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    timestamp: datetime = Field(default_factory=utc_now, index=True)
    level: ActivityLevel = Field(default=ActivityLevel.INFO)
    event_type: ActivityEvent = Field(index=True)
    title: str = Field(max_length=200)
    description: str | None = Field(default=None, max_length=2000)

    project_id: uuid.UUID | None = Field(
        default=None, foreign_key="projects.id", index=True
    )
    target_id: uuid.UUID | None = Field(
        default=None, foreign_key="targets.id", index=True
    )
    user_id: uuid.UUID | None = Field(default=None, foreign_key="users.id", index=True)


class ActivityLogRead(BaseModel):
    """Read schema for API responses and SSE payloads."""

    id: uuid.UUID
    timestamp: datetime
    level: ActivityLevel
    event_type: ActivityEvent
    title: str
    description: str | None = None
    project_id: uuid.UUID | None = None
    target_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
