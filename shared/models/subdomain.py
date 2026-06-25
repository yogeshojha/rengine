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
    is_important: bool = Field(default=False)

    http_url: str | None = Field(default=None, max_length=2000)
    http_status: int | None = Field(default=None, index=True)
    page_title: str | None = Field(default=None, max_length=1000)
    content_type: str | None = Field(default=None, max_length=255)
    content_length: int | None = Field(default=None)
    response_time: float | None = Field(default=None)
    webserver: str | None = Field(default=None, max_length=255)
    tech: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    is_cdn: bool = Field(default=False)
    cdn_name: str | None = Field(default=None, max_length=100)
    screenshot_path: str | None = Field(default=None, max_length=500)

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
    is_important: bool = False
    http_url: str | None = None
    http_status: int | None = None
    page_title: str | None = None
    content_type: str | None = None
    content_length: int | None = None
    response_time: float | None = None
    webserver: str | None = None
    tech: list[str] = Field(default_factory=list)
    is_cdn: bool = False
    cdn_name: str | None = None
    screenshot_path: str | None = None
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
    is_important: bool = False
    http_status: int | None = None
    page_title: str | None = None
    content_length: int | None = None
    response_time: float | None = None
    webserver: str | None = None
    tech: list[str] = Field(default_factory=list)
    is_cdn: bool = False
    cdn_name: str | None = None
    screenshot_path: str | None = None
    scan_count: int
    last_scan_id: uuid.UUID
    first_seen: datetime
    last_seen: datetime
