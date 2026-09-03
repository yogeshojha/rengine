import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel
from sqlalchemy import Column, Computed, Text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel, UniqueConstraint

from shared.utils.datetime import utc_now

HEADER_SEARCH_LIMIT = 20_000
BODY_SEARCH_LIMIT = 100_000
SEARCH_TSV_SQL = (
    "setweight(to_tsvector('simple', "
    f"left(coalesce(raw_response_header, ''), {HEADER_SEARCH_LIMIT})), 'A') || "
    "setweight(to_tsvector('simple', "
    f"left(coalesce(response_body, ''), {BODY_SEARCH_LIMIT})), 'B')"
)


def _json_list() -> Field:
    return Field(default_factory=list, sa_column=Column(JSON, nullable=False))


def _text() -> Field:
    return Field(default=None, sa_column=Column(Text, nullable=True))


class HttpAsset(SQLModel, table=True):
    __tablename__ = "http_assets"
    __table_args__ = (UniqueConstraint("scan_id", "url", name="uq_httpasset_scan_url"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    scan_id: uuid.UUID = Field(foreign_key="scans.id", index=True, ondelete="CASCADE")
    target_id: uuid.UUID = Field(
        foreign_key="targets.id", index=True, ondelete="CASCADE"
    )
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)

    # request
    url: str = Field(max_length=2000)
    final_url: str | None = Field(default=None, max_length=2000)
    host: str = Field(max_length=500, index=True)
    port: int = Field(default=0)
    scheme: str = Field(default="https", max_length=8)
    method: str | None = Field(default=None, max_length=10)
    path: str | None = Field(default=None, max_length=2000)

    # response
    status_code: int | None = Field(default=None, index=True)
    chain_status_codes: list = _json_list()
    title: str | None = Field(default=None, max_length=1000)
    webserver: str | None = Field(default=None, max_length=255)
    content_type: str | None = Field(default=None, max_length=255)
    content_length: int | None = Field(default=None)
    location: str | None = Field(default=None, max_length=2000)
    response_time: float | None = Field(default=None)
    words: int | None = Field(default=None)
    lines: int | None = Field(default=None)

    # fingerprint
    tech: list = _json_list()
    cpe: list = _json_list()
    favicon_hash: str | None = Field(default=None, max_length=64)
    favicon_path: str | None = Field(default=None, max_length=2000)
    content_hash: str | None = Field(default=None, max_length=80)
    header_hash: str | None = Field(default=None, max_length=80)
    jarm: str | None = Field(default=None, max_length=64)
    supports_http2: bool = Field(default=False)
    supports_pipeline: bool = Field(default=False)

    # network
    ip: str | None = Field(default=None, max_length=45, index=True)
    a_records: list = _json_list()
    aaaa_records: list = _json_list()
    cname: str | None = Field(default=None, max_length=500)
    asn: int | None = Field(default=None)
    asn_org: str | None = Field(default=None, max_length=255)
    is_cdn: bool = Field(default=False, index=True)
    cdn_name: str | None = Field(default=None, max_length=100)
    cdn_type: str | None = Field(default=None, max_length=20)
    waf: str | None = Field(default=None, max_length=100)

    # tls
    tls_version: str | None = Field(default=None, max_length=20)
    tls_cipher: str | None = Field(default=None, max_length=100)
    tls_subject_cn: str | None = Field(default=None, max_length=500)
    tls_subject_dn: str | None = Field(default=None, max_length=1000)
    tls_sans: list = _json_list()
    tls_issuer: str | None = Field(default=None, max_length=500)
    tls_issuer_cn: str | None = Field(default=None, max_length=500)
    tls_issuer_org: str | None = Field(default=None, max_length=500)
    tls_serial: str | None = Field(default=None, max_length=200)
    tls_fingerprint: str | None = Field(default=None, max_length=80)
    tls_not_before: datetime | None = Field(default=None)
    tls_not_after: datetime | None = Field(default=None)
    tls_expired: bool | None = Field(default=None)
    tls_self_signed: bool | None = Field(default=None)

    screenshot_path: str | None = Field(default=None, max_length=500)

    # raw capture (httpx -irr)
    raw_request: str | None = _text()
    raw_response_header: str | None = _text()
    response_body: str | None = _text()
    response_headers: dict = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    body_preview: str | None = Field(default=None, max_length=512)
    search_tsv: Any | None = Field(
        default=None,
        sa_column=Column(TSVECTOR, Computed(SEARCH_TSV_SQL, persisted=True)),
    )

    discovered_at: datetime = Field(default_factory=utc_now)
    created_at: datetime = Field(default_factory=utc_now)


class HttpAssetRead(BaseModel):
    id: uuid.UUID
    scan_id: uuid.UUID
    target_id: uuid.UUID
    url: str
    final_url: str | None = None
    host: str
    port: int
    scheme: str
    method: str | None = None
    path: str | None = None
    status_code: int | None = None
    chain_status_codes: list[int] = Field(default_factory=list)
    title: str | None = None
    webserver: str | None = None
    content_type: str | None = None
    content_length: int | None = None
    location: str | None = None
    response_time: float | None = None
    words: int | None = None
    lines: int | None = None
    tech: list[str] = Field(default_factory=list)
    cpe: list = Field(default_factory=list)
    favicon_hash: str | None = None
    content_hash: str | None = None
    header_hash: str | None = None
    jarm: str | None = None
    supports_http2: bool = False
    supports_pipeline: bool = False
    ip: str | None = None
    a_records: list[str] = Field(default_factory=list)
    aaaa_records: list[str] = Field(default_factory=list)
    cname: str | None = None
    asn: int | None = None
    asn_org: str | None = None
    is_cdn: bool = False
    cdn_name: str | None = None
    cdn_type: str | None = None
    waf: str | None = None
    tls_version: str | None = None
    tls_cipher: str | None = None
    tls_subject_cn: str | None = None
    tls_sans: list[str] = Field(default_factory=list)
    tls_issuer: str | None = None
    tls_issuer_org: str | None = None
    tls_serial: str | None = None
    tls_fingerprint: str | None = None
    tls_not_before: datetime | None = None
    tls_not_after: datetime | None = None
    tls_expired: bool | None = None
    tls_self_signed: bool | None = None
    screenshot_path: str | None = None
    body_preview: str | None = None
    discovered_at: datetime


class HttpAssetDetail(HttpAssetRead):
    tls_subject_dn: str | None = None
    tls_issuer_cn: str | None = None
    raw_request: str | None = None
    raw_response_header: str | None = None
    response_body: str | None = None
    response_headers: dict = Field(default_factory=dict)


class HttpAssetSummary(BaseModel):
    total: int
    by_status: dict[str, int] = Field(default_factory=dict)
    by_tech: dict[str, int] = Field(default_factory=dict)
    cdn: int = 0
