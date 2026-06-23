import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel

from shared.enums.scan import ScanActivityStatus
from shared.utils.datetime import utc_now


class ScanCommand(SQLModel, table=True):
    __tablename__ = "scan_commands"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    scan_id: uuid.UUID = Field(foreign_key="scans.id", index=True, ondelete="CASCADE")
    activity_id: uuid.UUID | None = Field(
        default=None, foreign_key="scan_activities.id", index=True, ondelete="CASCADE"
    )
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)

    tool: str = Field(max_length=100, index=True)
    command: str = Field(sa_column=Column(Text, nullable=False))
    status: str = Field(default=ScanActivityStatus.RUNNING.value, index=True)
    return_code: int | None = Field(default=None)
    output: str | None = Field(default=None, sa_column=Column(Text))
    error: str | None = Field(default=None, max_length=2000)
    duration_seconds: float | None = Field(default=None)

    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = Field(default=None)


class ScanCommandRead(BaseModel):
    id: uuid.UUID
    scan_id: uuid.UUID
    activity_id: uuid.UUID | None = None
    tool: str
    command: str
    status: str
    return_code: int | None = None
    error: str | None = None
    duration_seconds: float | None = None
    started_at: datetime
    completed_at: datetime | None = None


class ScanCommandDetail(ScanCommandRead):
    output: str | None = None
