import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel, UniqueConstraint

from shared.utils.datetime import utc_now


class Subdomain(SQLModel, table=True):
    __tablename__ = "subdomains"
    __table_args__ = (
        UniqueConstraint("scan_id", "name", name="uq_subdomain_scan_name"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    scan_id: uuid.UUID = Field(foreign_key="scans.id", index=True, ondelete="CASCADE")
    target_id: uuid.UUID = Field(
        foreign_key="targets.id", index=True, ondelete="CASCADE"
    )
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)

    name: str = Field(max_length=500, index=True)
    sources: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    resolved_ips: list = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    cname: str | None = Field(default=None, max_length=500)
    is_active: bool = Field(default=False, index=True)
    is_wildcard: bool = Field(default=False)
    is_excluded: bool = Field(default=False, index=True)

    discovered_at: datetime = Field(default_factory=utc_now)
    created_at: datetime = Field(default_factory=utc_now)


class SubdomainRead(BaseModel):
    id: uuid.UUID
    scan_id: uuid.UUID
    target_id: uuid.UUID
    name: str
    sources: list[str] = Field(default_factory=list)
    resolved_ips: list[str] = Field(default_factory=list)
    cname: str | None = None
    is_active: bool
    is_wildcard: bool
    is_excluded: bool = False
    discovered_at: datetime


class SubdomainSummary(BaseModel):
    total: int
    active: int
    sources: dict[str, int] = Field(default_factory=dict)


class TargetSubdomainRead(BaseModel):
    name: str
    sources: list[str] = Field(default_factory=list)
    resolved_ips: list[str] = Field(default_factory=list)
    cname: str | None = None
    is_active: bool
    is_wildcard: bool
    is_excluded: bool = False
    scan_count: int
    last_scan_id: uuid.UUID
    first_seen: datetime
    last_seen: datetime
