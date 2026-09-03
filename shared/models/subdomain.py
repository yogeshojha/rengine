import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel, UniqueConstraint

from shared.definitions.asset_query import MAX_QUERY_LENGTH
from shared.models.asset_query import MatchEvidence, QueryError
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
    final_url: str | None = Field(default=None, max_length=2000)
    http_status: int | None = Field(default=None, index=True)
    page_title: str | None = Field(default=None, max_length=1000)
    content_type: str | None = Field(default=None, max_length=255)
    content_length: int | None = Field(default=None)
    response_time: float | None = Field(default=None)
    webserver: str | None = Field(default=None, max_length=255)
    tech: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    is_cdn: bool = Field(default=False)
    cdn_name: str | None = Field(default=None, max_length=100)
    waf: str | None = Field(default=None, max_length=100)
    asn: int | None = Field(default=None)
    asn_org: str | None = Field(default=None, max_length=255)
    favicon_hash: str | None = Field(default=None, max_length=64)
    tls_not_after: datetime | None = Field(default=None)
    tls_expired: bool | None = Field(default=None)
    tls_self_signed: bool | None = Field(default=None)
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
    final_url: str | None = None
    http_status: int | None = None
    page_title: str | None = None
    content_type: str | None = None
    content_length: int | None = None
    response_time: float | None = None
    webserver: str | None = None
    tech: list[str] = Field(default_factory=list)
    is_cdn: bool = False
    cdn_name: str | None = None
    waf: str | None = None
    asn: int | None = None
    asn_org: str | None = None
    favicon_hash: str | None = None
    tls_not_after: datetime | None = None
    tls_expired: bool | None = None
    tls_self_signed: bool | None = None
    screenshot_path: str | None = None
    discovered_at: datetime


class SubdomainRow(SubdomainRead):
    ports: list[int] = Field(default_factory=list)
    title_count: int = 0
    favicon_count: int = 0
    matched_in: list[MatchEvidence] = Field(default_factory=list)


class SubdomainSummary(BaseModel):
    total: int
    active: int
    sources: dict[str, int] = Field(default_factory=dict)


class Facet(BaseModel):
    value: str
    label: str
    count: int


class SubdomainFilter(BaseModel):
    q: str | None = Field(default=None, max_length=MAX_QUERY_LENGTH)
    statuses: list[str] = Field(default_factory=list, max_length=10)
    tech: list[str] = Field(default_factory=list, max_length=200)
    services: list[str] = Field(default_factory=list, max_length=200)
    cert: list[str] = Field(default_factory=list, max_length=10)
    sources: list[str] = Field(default_factory=list, max_length=200)
    cdn: str = Field(default="any", max_length=10)
    waf: str = Field(default="any", max_length=20)
    live: bool = False
    screenshot: bool = False
    issues: bool = False
    new: bool = False
    sort: str = Field(default="name", max_length=20)
    order: str = Field(default="asc", max_length=4)
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0, le=100_000_000)


class SubdomainSearchResult(BaseModel):
    items: list[SubdomainRow] = Field(default_factory=list)
    total: int = 0
    total_capped: bool = False
    error: QueryError | None = None


class SubdomainFacets(BaseModel):
    status: list[Facet] = Field(default_factory=list)
    tech: list[Facet] = Field(default_factory=list)
    service: list[Facet] = Field(default_factory=list)
    source: list[Facet] = Field(default_factory=list)
    cert: list[Facet] = Field(default_factory=list)


class SubdomainRelation(BaseModel):
    kind: str
    reason: str
    value: str
    hosts: list[str] = Field(default_factory=list)


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
    waf: str | None = None
    tls_not_after: datetime | None = None
    tls_expired: bool | None = None
    screenshot_path: str | None = None
    scan_count: int
    last_scan_id: uuid.UUID
    first_seen: datetime
    last_seen: datetime
