import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel, UniqueConstraint

from shared.utils.datetime import utc_now


class HttpAsset(SQLModel, table=True):
    __tablename__ = "http_assets"
    __table_args__ = (UniqueConstraint("scan_id", "url", name="uq_httpasset_scan_url"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    scan_id: uuid.UUID = Field(foreign_key="scans.id", index=True, ondelete="CASCADE")
    target_id: uuid.UUID = Field(
        foreign_key="targets.id", index=True, ondelete="CASCADE"
    )
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)

    url: str = Field(max_length=2000)
    host: str = Field(max_length=500, index=True)
    port: int = Field(default=0)
    scheme: str = Field(default="https", max_length=8)

    status_code: int | None = Field(default=None, index=True)
    title: str | None = Field(default=None, max_length=1000)
    webserver: str | None = Field(default=None, max_length=255)
    content_length: int | None = Field(default=None)
    content_type: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=2000)
    final_url: str | None = Field(default=None, max_length=2000)

    tech: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    ip: str | None = Field(default=None, max_length=45)
    cname: str | None = Field(default=None, max_length=500)
    asn: int | None = Field(default=None)
    asn_org: str | None = Field(default=None, max_length=255)
    is_cdn: bool = Field(default=False, index=True)
    cdn_name: str | None = Field(default=None, max_length=100)
    waf: str | None = Field(default=None, max_length=100)
    jarm: str | None = Field(default=None, max_length=64)
    favicon_hash: str | None = Field(default=None, max_length=64)
    content_hash: str | None = Field(default=None, max_length=80)

    tls_issuer: str | None = Field(default=None, max_length=500)
    tls_subject_cn: str | None = Field(default=None, max_length=500)
    tls_sans: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    tls_not_after: datetime | None = Field(default=None)
    tls_self_signed: bool | None = Field(default=None)
    tls_expired: bool | None = Field(default=None)
    tls_version: str | None = Field(default=None, max_length=20)

    screenshot_path: str | None = Field(default=None, max_length=500)

    discovered_at: datetime = Field(default_factory=utc_now)
    created_at: datetime = Field(default_factory=utc_now)


class HttpAssetRead(BaseModel):
    id: uuid.UUID
    scan_id: uuid.UUID
    target_id: uuid.UUID
    url: str
    host: str
    port: int
    scheme: str
    status_code: int | None = None
    title: str | None = None
    webserver: str | None = None
    content_length: int | None = None
    content_type: str | None = None
    location: str | None = None
    final_url: str | None = None
    tech: list[str] = Field(default_factory=list)
    ip: str | None = None
    cname: str | None = None
    asn: int | None = None
    asn_org: str | None = None
    is_cdn: bool = False
    cdn_name: str | None = None
    waf: str | None = None
    jarm: str | None = None
    favicon_hash: str | None = None
    content_hash: str | None = None
    tls_issuer: str | None = None
    tls_subject_cn: str | None = None
    tls_sans: list[str] = Field(default_factory=list)
    tls_not_after: datetime | None = None
    tls_self_signed: bool | None = None
    tls_expired: bool | None = None
    tls_version: str | None = None
    screenshot_path: str | None = None
    discovered_at: datetime


class HttpAssetSummary(BaseModel):
    total: int
    by_status: dict[str, int] = Field(default_factory=dict)
    by_tech: dict[str, int] = Field(default_factory=dict)
    cdn: int = 0
