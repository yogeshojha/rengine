import uuid
from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy import UniqueConstraint
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel

from shared.definitions.cloud_storage import (
    MAX_NAME_LENGTH,
    MAX_URL_LENGTH,
    PROVIDER_ORDER,
    ReviewState,
)
from shared.utils.datetime import utc_now


class CloudBucket(SQLModel, table=True):
    __tablename__ = "cloud_buckets"
    __table_args__ = (
        UniqueConstraint(
            "scan_id", "provider", "name", name="uq_cloud_buckets_scan_provider_name"
        ),
    )

    id: uuid.UUID = SQLField(default_factory=uuid.uuid4, primary_key=True)
    scan_id: uuid.UUID = SQLField(
        foreign_key="scans.id", index=True, ondelete="CASCADE"
    )
    target_id: uuid.UUID = SQLField(
        foreign_key="targets.id", index=True, ondelete="CASCADE"
    )
    project_id: uuid.UUID = SQLField(foreign_key="projects.id", index=True)

    name: str = SQLField(max_length=MAX_NAME_LENGTH, index=True)
    provider: str = SQLField(max_length=24)
    url: str = SQLField(max_length=MAX_URL_LENGTH)
    source: str = SQLField(max_length=16)
    access: str = SQLField(max_length=16, index=True)
    region: str | None = SQLField(default=None, max_length=32)

    object_count: int | None = SQLField(default=None)
    size: int | None = SQLField(default=None)

    first_seen: datetime = SQLField(default_factory=utc_now)
    discovered_at: datetime = SQLField(default_factory=utc_now)
    created_at: datetime = SQLField(default_factory=utc_now)


class CloudBucketTriage(SQLModel, table=True):
    __tablename__ = "cloud_bucket_triage"
    __table_args__ = (
        UniqueConstraint(
            "target_id",
            "provider",
            "name",
            name="uq_cloud_bucket_triage_target_provider_name",
        ),
    )

    id: uuid.UUID = SQLField(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = SQLField(foreign_key="projects.id", index=True)
    target_id: uuid.UUID = SQLField(
        foreign_key="targets.id", index=True, ondelete="CASCADE"
    )
    provider: str = SQLField(max_length=24)
    name: str = SQLField(max_length=MAX_NAME_LENGTH)
    state: str = SQLField(default=ReviewState.OPEN.value, max_length=16)
    updated_at: datetime = SQLField(default_factory=utc_now)


class CloudBucketRead(BaseModel):
    id: uuid.UUID
    scan_id: uuid.UUID
    target_id: uuid.UUID
    name: str
    provider: str
    url: str
    source: str
    access: str
    region: str | None = None
    object_count: int | None = None
    size: int | None = None
    first_seen: datetime
    discovered_at: datetime
    state: str = ReviewState.OPEN.value


class CloudBucketSummary(BaseModel):
    """Buckets of one scan, counted by access and provider."""

    covered: bool = False
    scan_id: uuid.UUID | None = None
    target_id: uuid.UUID | None = None
    observed_at: datetime | None = None
    candidates: int | None = None
    rows: list[CloudBucketRead] = Field(default_factory=list)
    access_counts: dict[str, int] = Field(default_factory=dict)
    provider_counts: dict[str, int] = Field(
        default_factory=lambda: dict.fromkeys(PROVIDER_ORDER, 0)
    )
    open_count: int = 0
    total: int = 0


class CloudBucketTriageUpdate(BaseModel):
    target_id: uuid.UUID
    buckets: list[tuple[str, str]] = Field(min_length=1, max_length=500)
    state: ReviewState
