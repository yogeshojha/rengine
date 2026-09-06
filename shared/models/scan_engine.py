import uuid
from datetime import datetime

from pydantic import BaseModel
from pydantic import Field as PydanticField
from sqlalchemy import Column
from sqlalchemy.types import JSON, Text
from sqlmodel import Field, SQLModel

from shared.definitions.constants import DEFAULT_GLOBAL_THREADS
from shared.models.scan_context import ScanContextCreate
from shared.utils.datetime import utc_now


class ScanEngine(SQLModel, table=True):
    __tablename__ = "scan_engines"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)
    created_by: uuid.UUID = Field(foreign_key="users.id")
    name: str = Field(max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    intensity: str = Field(default="normal")
    global_threads: int = Field(default=DEFAULT_GLOBAL_THREADS)
    global_http_crawl: bool = Field(default=True)
    global_headers: list = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    stages: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    yaml_source: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    tool_options: dict = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    last_used_at: datetime | None = Field(default=None)


class ScanEngineCreate(BaseModel):
    name: str
    description: str | None = None
    intensity: str = "normal"
    global_threads: int = DEFAULT_GLOBAL_THREADS
    global_http_crawl: bool = True
    global_headers: list[str] = PydanticField(default_factory=list)
    stages: dict[str, dict] = PydanticField(default_factory=dict)
    yaml_source: str | None = None
    tool_options: dict[str, str] = PydanticField(default_factory=dict)


class ScanEngineUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    intensity: str | None = None
    global_threads: int | None = None
    global_http_crawl: bool | None = None
    global_headers: list[str] | None = None
    stages: dict[str, dict] | None = None
    yaml_source: str | None = None
    tool_options: dict[str, str] | None = None


class EngineUsage(BaseModel):
    schedules: int = 0
    scans: int = 0


class ScanEngineRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    created_by: uuid.UUID
    name: str
    description: str | None
    intensity: str
    global_threads: int
    global_http_crawl: bool
    global_headers: list[str]
    stages: dict[str, dict]
    yaml_source: str | None
    tool_options: dict[str, str] = PydanticField(default_factory=dict)
    usage: EngineUsage = PydanticField(default_factory=EngineUsage)
    created_at: datetime
    updated_at: datetime
    last_used_at: datetime | None


class StageField(BaseModel):
    name: str
    title: str
    description: str | None = None
    type: str
    default: object = None
    options: list[str] | None = None
    option_labels: dict[str, str] | None = None
    minimum: int | None = None
    maximum: int | None = None
    scale: str | None = None
    widget: str | None = None
    # what a widget selects, when the widget needs it (wordlist kind)
    kind: str | None = None
    launch: bool = False


class StageCatalogEntry(BaseModel):
    name: str
    title: str
    description: str
    phase: str
    level: int
    applies_to: list[str]
    tools: list[str]
    api_keys: list[str]
    requires_api_keys: bool = False
    touches_target: bool = True
    launch_fields: list[str] = PydanticField(default_factory=list)
    group: str
    role: str
    consumes: list[str] = PydanticField(default_factory=list)
    produces: list[str] = PydanticField(default_factory=list)
    defaults: dict
    fields: list[StageField] = PydanticField(default_factory=list)


class StageGroupEntry(BaseModel):
    key: str
    label: str


class ToolOption(BaseModel):
    name: str
    label: str
    phase: str
    example: str


class EnginePreset(BaseModel):
    name: str
    title: str
    description: str
    stages: dict[str, dict]


class EngineCatalog(BaseModel):
    phases: list[str]
    stages: list[StageCatalogEntry]
    rate_tools: list[str]
    tool_options: list[ToolOption]
    presets: list[EnginePreset]
    target_types: list[str]
    groups: list[StageGroupEntry] = PydanticField(default_factory=list)
    seed_produces: dict[str, list[str]] = PydanticField(default_factory=dict)


class PreviewResolved(BaseModel):
    header_names: list[str] = PydanticField(default_factory=list)
    global_threads: int = DEFAULT_GLOBAL_THREADS
    global_rate_limit_ceiling: int | None = None
    per_tool_rate_limits: dict[str, int] = PydanticField(default_factory=dict)
    excluded_subdomains: list[str] = PydanticField(default_factory=list)
    excluded_paths: list[str] = PydanticField(default_factory=list)
    excluded_ips: list[str] = PydanticField(default_factory=list)
    included_subdomains: list[str] = PydanticField(default_factory=list)
    follow_redirects: bool | None = None
    http_protocol: str = "both"


class EnginePreviewResult(BaseModel):
    phases: list = PydanticField(default_factory=list)
    resolved_stages: dict[str, dict] = PydanticField(default_factory=dict)
    resolved: PreviewResolved = PydanticField(default_factory=PreviewResolved)
    warnings: list[str] = PydanticField(default_factory=list)


class EnginePreviewRequest(BaseModel):
    target_type: str
    context_id: uuid.UUID | None = None
    context: ScanContextCreate | None = None
    intensity: str = "normal"
    global_threads: int = DEFAULT_GLOBAL_THREADS
    stages: dict[str, dict] = PydanticField(default_factory=dict)
