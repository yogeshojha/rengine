import uuid
from datetime import datetime

from pydantic import BaseModel
from pydantic import Field as PydanticField
from sqlalchemy import Column, Text
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel, UniqueConstraint

from shared.definitions.vulnerabilities import (
    MAX_SELECTED_TEMPLATES,
    MAX_TEMPLATE_BYTES,
    MAX_TEMPLATE_UPLOAD,
    Protocol,
    Severity,
    TemplateOrigin,
)
from shared.utils.datetime import utc_now


def _json_list() -> Field:
    return Field(default_factory=list, sa_column=Column(JSON, nullable=False))


class VulnTemplate(SQLModel, table=True):
    """One check in the library. Project templates and uploads share the row shape."""

    __tablename__ = "vuln_templates"
    __table_args__ = (
        UniqueConstraint("origin", "path", name="uq_vulntemplate_origin_path"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    origin: str = Field(
        default=TemplateOrigin.OFFICIAL.value, max_length=16, index=True
    )
    template_id: str = Field(max_length=200, index=True)
    path: str = Field(max_length=500)
    name: str = Field(max_length=500)
    severity: str = Field(default=Severity.UNKNOWN.value, max_length=16, index=True)
    protocol: str = Field(default=Protocol.OTHER.value, max_length=16, index=True)
    directory: str = Field(default="", max_length=200, index=True)
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    remediation: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    tags: list = _json_list()
    authors: list = _json_list()
    references: list = _json_list()
    cve_ids: list = _json_list()
    cwe_ids: list = _json_list()
    cvss_score: float | None = Field(default=None)
    requests: int = Field(default=0)
    digest: str = Field(default="", max_length=64)
    raw: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    enabled: bool = Field(default=True, index=True)
    uploaded_by: uuid.UUID | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class VulnTemplateRead(BaseModel):
    id: uuid.UUID
    origin: str
    template_id: str
    path: str
    name: str
    severity: str
    protocol: str
    directory: str
    description: str | None = None
    remediation: str | None = None
    tags: list[str] = PydanticField(default_factory=list)
    authors: list[str] = PydanticField(default_factory=list)
    references: list[str] = PydanticField(default_factory=list)
    cve_ids: list[str] = PydanticField(default_factory=list)
    cwe_ids: list[str] = PydanticField(default_factory=list)
    cvss_score: float | None = None
    requests: int = 0
    enabled: bool = True
    sets: list[str] = PydanticField(default_factory=list)
    findings: int = 0
    raw: str | None = None
    created_at: datetime
    updated_at: datetime


class VulnTemplateUpload(BaseModel):
    filename: str = PydanticField(max_length=200)
    content: str = PydanticField(max_length=MAX_TEMPLATE_BYTES)


class VulnTemplateUploadRequest(BaseModel):
    files: list[VulnTemplateUpload] = PydanticField(
        default_factory=list, max_length=MAX_TEMPLATE_UPLOAD
    )


class VulnTemplateRejection(BaseModel):
    filename: str
    reason: str


class VulnTemplateUploadResult(BaseModel):
    accepted: list[VulnTemplateRead] = PydanticField(default_factory=list)
    replaced: int = 0
    rejected: list[VulnTemplateRejection] = PydanticField(default_factory=list)


class VulnTemplateUpdate(BaseModel):
    enabled: bool | None = None


class TemplateSource(BaseModel):
    id: uuid.UUID
    template_id: str
    name: str
    origin: str
    path: str
    editable: bool
    content: str


class TemplateSourceUpdate(BaseModel):
    content: str = PydanticField(max_length=MAX_TEMPLATE_BYTES)


class TemplateFilter(BaseModel):
    q: str | None = PydanticField(default=None, max_length=200)
    origins: list[str] = PydanticField(default_factory=list, max_length=4)
    severities: list[str] = PydanticField(default_factory=list, max_length=8)
    protocols: list[str] = PydanticField(default_factory=list, max_length=12)
    sets: list[str] = PydanticField(default_factory=list, max_length=40)
    tags: list[str] = PydanticField(default_factory=list, max_length=40)
    fired: bool = False
    limit: int = PydanticField(default=50, ge=1, le=200)
    offset: int = PydanticField(default=0, ge=0, le=1_000_000)


class TemplatePage(BaseModel):
    items: list[VulnTemplateRead] = PydanticField(default_factory=list)
    total: int = 0


class TemplateSetSpec(BaseModel):
    key: str
    label: str
    description: str
    headless: bool = False
    count: int = 0


class TemplateSelection(BaseModel):
    """The vulnerability plan as the user expressed it, resolved against the library."""

    severities: list[str] = PydanticField(default_factory=list, max_length=8)
    template_sets: list[str] = PydanticField(default_factory=list, max_length=40)
    custom_templates: list[uuid.UUID] = PydanticField(
        default_factory=list, max_length=MAX_SELECTED_TEMPLATES
    )
    include_tags: list[str] = PydanticField(default_factory=list, max_length=40)
    exclude_tags: list[str] = PydanticField(default_factory=list, max_length=40)
    exclude_templates: list[str] = PydanticField(default_factory=list, max_length=200)
    headless: bool = False


class SelectionBreakdown(BaseModel):
    key: str
    label: str
    count: int


class SelectionPreview(BaseModel):
    """What the current plan would run, counted against the indexed library."""

    ready: bool = False
    total: int = 0
    official: int = 0
    custom: int = 0
    by_severity: list[SelectionBreakdown] = PydanticField(default_factory=list)
    by_set: list[SelectionBreakdown] = PydanticField(default_factory=list)
    by_protocol: list[SelectionBreakdown] = PydanticField(default_factory=list)
    estimated_requests: int = 0
    warnings: list[str] = PydanticField(default_factory=list)


class TemplateLibraryStats(BaseModel):
    ready: bool = False
    total: int = 0
    official: int = 0
    custom: int = 0
    by_severity: list[SelectionBreakdown] = PydanticField(default_factory=list)
    by_protocol: list[SelectionBreakdown] = PydanticField(default_factory=list)
    sets: list[TemplateSetSpec] = PydanticField(default_factory=list)
    tags: list[SelectionBreakdown] = PydanticField(default_factory=list)
    fired: int = 0
    last_synced_at: datetime | None = None
    syncing: bool = False


class TemplateSyncResult(BaseModel):
    started: bool = False
    message: str = ""
