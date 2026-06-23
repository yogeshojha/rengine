import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column, Text
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from shared.enums.scan import ScanActivityStatus
from shared.utils.datetime import utc_now


class ScanActivity(SQLModel, table=True):
    __tablename__ = "scan_activities"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    scan_id: uuid.UUID = Field(foreign_key="scans.id", index=True, ondelete="CASCADE")
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)

    name: str = Field(max_length=100, index=True)
    title: str = Field(max_length=200)
    status: str = Field(default=ScanActivityStatus.PENDING.value, index=True)
    celery_task_id: str | None = Field(default=None, max_length=100)
    error: str | None = Field(default=None, max_length=2000)
    traceback: str | None = Field(default=None, sa_column=Column(Text))
    result: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))

    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)


class ScanActivityRead(BaseModel):
    id: uuid.UUID
    scan_id: uuid.UUID
    name: str
    title: str
    status: str
    error: str | None = None
    result: dict = Field(default_factory=dict)
    command_count: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    created_at: datetime
