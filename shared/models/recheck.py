import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from shared.utils.datetime import utc_now


class AssetRecheck(SQLModel, table=True):
    __tablename__ = "asset_rechecks"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)
    target_id: uuid.UUID = Field(
        foreign_key="targets.id", index=True, ondelete="CASCADE"
    )
    scan_id: uuid.UUID = Field(foreign_key="scans.id", index=True, ondelete="CASCADE")
    parent_scan_id: uuid.UUID = Field(
        foreign_key="scans.id", index=True, ondelete="CASCADE"
    )
    dimension: str = Field(max_length=32)
    asset_kind: str = Field(max_length=16)
    asset_key: str = Field(max_length=500, index=True)
    changed: bool = Field(default=False)
    changes: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(default_factory=utc_now)


class RecheckChange(BaseModel):
    field: str
    label: str
    before: str | None = None
    after: str | None = None
    tone: str = "neutral"


class RecheckRead(BaseModel):
    id: uuid.UUID
    scan_id: uuid.UUID
    parent_scan_id: uuid.UUID
    dimension: str
    asset_kind: str
    asset_key: str
    changed: bool
    changes: list[RecheckChange]
    created_at: datetime
    status: str
    stage_titles: list[str] = []
    duration_seconds: float | None = None
