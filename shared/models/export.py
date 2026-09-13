import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField
from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from shared.definitions.exports import (
    ExportFormat,
    ExportScope,
    ExportStatus,
)
from shared.utils.datetime import utc_now

MAX_SUBJECT_LEN = 200
MAX_FILENAME_LEN = 255
MAX_ERROR_LEN = 2000


class Export(SQLModel, table=True):
    """A saved export: the recipe it was run from, and the file that run produced."""

    __tablename__ = "exports"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)
    created_by: uuid.UUID | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now, index=True)

    # the recipe — everything a re-run needs
    dimension: str = Field(max_length=32, index=True)
    scope: str = Field(default=ExportScope.SCAN.value, max_length=16)
    scan_id: uuid.UUID | None = Field(
        default=None, foreign_key="scans.id", index=True, ondelete="CASCADE"
    )
    target_id: uuid.UUID | None = Field(
        default=None, foreign_key="targets.id", index=True, ondelete="CASCADE"
    )
    subject: str = Field(default="", max_length=MAX_SUBJECT_LEN)
    query: str = Field(default="", max_length=2000)
    filters: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    export_format: str = Field(default=ExportFormat.CSV.value, max_length=16)
    include_evidence: bool = Field(default=False)

    status: str = Field(default=ExportStatus.QUEUED.value, max_length=16, index=True)
    progress: int = Field(default=0)
    step: str = Field(default="", max_length=100)
    error: str | None = Field(default=None, max_length=MAX_ERROR_LEN)
    task_id: str | None = Field(default=None, max_length=100)

    filename: str | None = Field(default=None, max_length=MAX_FILENAME_LEN)
    bytes_written: int = Field(default=0)
    row_count: int = Field(default=0)
    total_rows: int = Field(default=0)
    capped: bool = Field(default=False)

    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    duration_seconds: float | None = Field(default=None)
    expires_at: datetime | None = Field(default=None, index=True)


class ExportCreate(BaseModel):
    """A launch names a dimension, a scope and the filter the table is showing."""

    model_config = ConfigDict(extra="forbid")

    dimension: str = PydanticField(max_length=32)
    scan_id: uuid.UUID | None = None
    target_id: uuid.UUID | None = None
    export_format: str = PydanticField(default=ExportFormat.CSV.value, max_length=16)
    filters: dict = PydanticField(default_factory=dict)
    include_evidence: bool = False


class ExportRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    dimension: str
    scope: str
    scan_id: uuid.UUID | None
    target_id: uuid.UUID | None
    subject: str
    query: str
    export_format: str
    include_evidence: bool
    status: str
    progress: int
    step: str
    error: str | None
    filename: str | None
    bytes_written: int
    row_count: int
    total_rows: int
    capped: bool
    created_at: datetime
    completed_at: datetime | None
    duration_seconds: float | None
    expires_at: datetime | None
