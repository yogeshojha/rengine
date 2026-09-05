import uuid
from datetime import datetime

from pydantic import BaseModel, Field

MAX_ASSET_SEARCH = 200

ASSET_STATES: tuple[str, ...] = ("all", "current", "new", "gone")
ASSET_SORTS: tuple[str, ...] = ("name", "first_seen", "last_seen", "scans", "status")


class TargetAssetRow(BaseModel):
    name: str
    is_active: bool = False
    is_wildcard: bool = False
    resolved_ips: list[str] = Field(default_factory=list)
    cname: str | None = None
    sources: list[str] = Field(default_factory=list)
    scan_count: int = 0
    first_seen: datetime
    last_seen: datetime
    last_scan_id: uuid.UUID
    current: bool = True
    is_new: bool = False
    status_code: int | None = None
    title: str | None = None
    webserver: str | None = None
    tech: list[str] = Field(default_factory=list)
    ip: str | None = None
    asn_org: str | None = None
    is_cdn: bool = False
    cdn_name: str | None = None
    screenshot_path: str | None = None


class TargetAssetFilter(BaseModel):
    search: str | None = Field(default=None, max_length=MAX_ASSET_SEARCH)
    state: str = Field(default="all", max_length=10)
    live: bool = False
    sort: str = Field(default="name", max_length=20)
    order: str = Field(default="asc", max_length=4)
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0, le=100_000_000)


class TargetAssetFacets(BaseModel):
    total: int = 0
    current: int = 0
    new: int = 0
    gone: int = 0
    live: int = 0
    baseline: bool = False
    latest_scan_id: uuid.UUID | None = None


class TargetAssetPage(BaseModel):
    items: list[TargetAssetRow] = Field(default_factory=list)
    total: int = 0
    facets: TargetAssetFacets = Field(default_factory=TargetAssetFacets)
