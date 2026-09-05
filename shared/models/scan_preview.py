import uuid
from enum import StrEnum

from pydantic import BaseModel, Field


class PreviewToolStatus(StrEnum):
    WILL_RUN = "will_run"
    SKIPPED_DISABLED = "skipped_disabled"
    SKIPPED_NEEDS_KEY = "skipped_needs_key"
    SKIPPED_NOT_APPLICABLE = "skipped_not_applicable"
    SKIPPED_NO_INPUT = "skipped_no_input"


class PreviewTool(BaseModel):
    capability: str
    label: str
    status: PreviewToolStatus
    reason: str | None = None
    rate: int | None = None
    threads: int | None = None
    timeout: int | None = None


class PreviewPhase(BaseModel):
    phase: str
    label: str
    tools: list[PreviewTool] = Field(default_factory=list)


class PreviewSummary(BaseModel):
    auth_summary: str
    custom_header_names: list[str] = Field(default_factory=list)
    rate_summary: str
    thread_multiplier: float
    timeout_multiplier: float
    http_protocol: str
    follow_redirects: bool | None = None
    excluded_subdomains_count: int = 0
    excluded_paths_count: int = 0
    excluded_ips_count: int = 0
    excluded_subdomains: list[str] = Field(default_factory=list)
    excluded_paths: list[str] = Field(default_factory=list)
    excluded_ips: list[str] = Field(default_factory=list)
    included_subdomains: list[str] = Field(default_factory=list)
    proxy_name: str | None = None
    estimated_duration_seconds: int = 0
    estimated_duration_human: str = ""


class ScanPreview(BaseModel):
    target_id: uuid.UUID | None = None
    target_value: str
    target_type: str
    engine_id: uuid.UUID | None = None
    engine_name: str
    context_id: uuid.UUID | None = None
    context_name: str | None = None
    phases: list[PreviewPhase] = Field(default_factory=list)
    summary: PreviewSummary
    warnings: list[str] = Field(default_factory=list)
