import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from shared.utils.datetime import utc_now

AUTH_TYPES = ("none", "header", "bearer", "basic", "cookie", "api_key")
HTTP_PROTOCOLS = ("both", "http_only", "https_only")


def valid_rate_tools() -> tuple[str, ...]:
    from stages.registry import rate_tools  # noqa: PLC0415

    return rate_tools()


MULTIPLIERS = (0.5, 1.0, 2.0)


class AuthConfig(BaseModel):
    auth_type: str = "none"
    bearer_token: str | None = None
    basic_username: str | None = None
    basic_password: str | None = None
    header_name: str | None = None
    header_value: str | None = None
    cookie_value: str | None = None
    api_key_name: str | None = None
    api_key_value: str | None = None


class AuthHeader(BaseModel):
    name: str
    value: str


class ScanContext(SQLModel, table=True):
    __tablename__ = "scan_contexts"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)
    created_by: uuid.UUID = Field(foreign_key="users.id")
    name: str = Field(max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    auth_type: str = Field(default="none")
    auth: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    extra_headers: list = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    global_rate_limit_override: int | None = Field(default=None)
    per_tool_rate_overrides: dict = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    thread_multiplier: float = Field(default=1.0)
    timeout_multiplier: float = Field(default=1.0)
    excluded_subdomains: list = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    excluded_paths: list = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    excluded_ips: list = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    included_subdomains: list = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    follow_redirects_override: bool | None = Field(default=None)
    http_protocol: str = Field(default="both")
    proxy_id: uuid.UUID | None = Field(default=None, index=True)
    compare_baseline_scan_id: uuid.UUID | None = Field(default=None)
    scan_only_new_assets: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    last_used_at: datetime | None = Field(default=None)
    last_used_scan_id: uuid.UUID | None = Field(default=None)


class ScanContextCreate(BaseModel):
    name: str
    description: str | None = None
    auth_type: str = "none"
    auth: AuthConfig | None = None
    extra_headers: list[AuthHeader] = Field(default_factory=list)
    global_rate_limit_override: int | None = None
    per_tool_rate_overrides: dict[str, int] = Field(default_factory=dict)
    thread_multiplier: float = 1.0
    timeout_multiplier: float = 1.0
    excluded_subdomains: list[str] = Field(default_factory=list)
    excluded_paths: list[str] = Field(default_factory=list)
    excluded_ips: list[str] = Field(default_factory=list)
    included_subdomains: list[str] = Field(default_factory=list)
    follow_redirects_override: bool | None = None
    http_protocol: str = "both"
    proxy_id: uuid.UUID | None = None
    compare_baseline_scan_id: uuid.UUID | None = None
    scan_only_new_assets: bool = False


class ScanContextUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    auth_type: str | None = None
    auth: AuthConfig | None = None
    extra_headers: list[AuthHeader] | None = None
    global_rate_limit_override: int | None = None
    per_tool_rate_overrides: dict[str, int] | None = None
    thread_multiplier: float | None = None
    timeout_multiplier: float | None = None
    excluded_subdomains: list[str] | None = None
    excluded_paths: list[str] | None = None
    excluded_ips: list[str] | None = None
    included_subdomains: list[str] | None = None
    follow_redirects_override: bool | None = None
    http_protocol: str | None = None
    proxy_id: uuid.UUID | None = None
    compare_baseline_scan_id: uuid.UUID | None = None
    scan_only_new_assets: bool | None = None


class ContextUsage(BaseModel):
    schedules: int = 0
    scans: int = 0


class ScanContextRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    created_by: uuid.UUID
    name: str
    description: str | None
    auth_type: str
    auth: AuthConfig
    auth_summary: str
    extra_headers: list[AuthHeader]
    global_rate_limit_override: int | None
    per_tool_rate_overrides: dict[str, int]
    thread_multiplier: float
    timeout_multiplier: float
    excluded_subdomains: list[str]
    excluded_paths: list[str]
    excluded_ips: list[str]
    included_subdomains: list[str]
    follow_redirects_override: bool | None
    http_protocol: str
    proxy_id: uuid.UUID | None
    compare_baseline_scan_id: uuid.UUID | None
    scan_only_new_assets: bool
    created_at: datetime
    updated_at: datetime
    last_used_at: datetime | None
    last_used_scan_id: uuid.UUID | None
    usage: ContextUsage = Field(default_factory=ContextUsage)
