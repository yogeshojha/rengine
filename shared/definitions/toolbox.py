"""Toolbox vocabulary: tool grouping, execution, run status and result blocks."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from shared.enums.target import TargetType


class ToolGroup(StrEnum):
    LOOKUP = "lookup"
    DISCOVERY = "discovery"
    INTEL = "intel"


GROUP_ORDER: tuple[str, ...] = (
    ToolGroup.LOOKUP.value,
    ToolGroup.DISCOVERY.value,
    ToolGroup.INTEL.value,
)

GROUP_LABELS: dict[str, str] = {
    ToolGroup.LOOKUP.value: "Lookup",
    ToolGroup.DISCOVERY.value: "Discovery",
    ToolGroup.INTEL.value: "Intelligence",
}


class InputKind(StrEnum):
    DOMAIN = TargetType.DOMAIN.value
    IP = TargetType.IP.value
    IP_RANGE = TargetType.IP_RANGE.value
    URL = TargetType.URL.value
    ASN = TargetType.ASN.value
    CVE = "cve"


INPUT_LABELS: dict[str, str] = {
    InputKind.DOMAIN.value: "Domain",
    InputKind.IP.value: "IP address",
    InputKind.IP_RANGE.value: "Address range",
    InputKind.URL.value: "URL",
    InputKind.ASN.value: "Autonomous system",
    InputKind.CVE.value: "CVE",
}


class ToolExecution(StrEnum):
    INLINE = "inline"
    QUEUED = "queued"


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


TERMINAL_STATUSES = frozenset({RunStatus.COMPLETED.value, RunStatus.FAILED.value})


class BlockKind(StrEnum):
    HERO = "hero"
    FACTS = "facts"
    TABLE = "table"
    TAGS = "tags"
    CODE = "code"
    NOTE = "note"
    IMAGE = "image"


class Tone(StrEnum):
    NEUTRAL = "neutral"
    SUCCESS = "success"
    WARNING = "warning"
    CRITICAL = "critical"
    INFO = "info"
    MUTED = "muted"


class IdentityKind(StrEnum):
    TECH = "tech"
    FLAG = "flag"
    FAVICON = "favicon"
    GLYPH = "glyph"
    NAMESERVER = "nameserver"


RUN_TTL_SECONDS = 7 * 24 * 3600
RUNS_KEPT = 40
RUNS_PER_MINUTE = 30
MAX_INPUT_LENGTH = 500
MAX_ROWS_PER_BLOCK = 2000


class Identity(BaseModel):
    kind: str
    value: str
    label: str | None = None


class Lookup(BaseModel):
    value: str
    tool: str | None = None


class Fact(BaseModel):
    label: str
    value: str
    tone: str = Tone.NEUTRAL.value
    note: str | None = None
    href: str | None = None
    mono: bool = False
    identity: Identity | None = None
    lookup: Lookup | None = None


class Cell(BaseModel):
    value: str
    tone: str = Tone.NEUTRAL.value
    note: str | None = None
    href: str | None = None
    mono: bool = False
    identity: Identity | None = None
    lookup: Lookup | None = None


class Tag(BaseModel):
    value: str
    tone: str = Tone.NEUTRAL.value
    note: str | None = None
    href: str | None = None
    identity: Identity | None = None
    lookup: Lookup | None = None


class Metric(BaseModel):
    value: str
    label: str | None = None
    tone: str = Tone.NEUTRAL.value


class Meter(BaseModel):
    value: float = Field(ge=0.0, le=1.0)
    label: str | None = None
    caption: str | None = None
    tone: str = Tone.NEUTRAL.value


class Mark(BaseModel):
    label: str
    tone: str = Tone.NEUTRAL.value
    note: str | None = None


class Block(BaseModel):
    kind: str
    title: str | None = None
    tone: str = Tone.NEUTRAL.value
    headline: str | None = None
    sub: str | None = None
    identity: Identity | None = None
    metric: Metric | None = None
    meter: Meter | None = None
    marks: list[Mark] = Field(default_factory=list)
    facts: list[Fact] = Field(default_factory=list)
    columns: list[str] = Field(default_factory=list)
    rows: list[list[Cell]] = Field(default_factory=list)
    tags: list[Tag] = Field(default_factory=list)
    text: str | None = None
    lang: str | None = None
    src: str | None = None
    empty: str | None = None
    total: int | None = None


class Pivot(BaseModel):
    label: str
    href: str | None = None
    dimension: str | None = None
    query: str | None = None


class ToolField(BaseModel):
    name: str
    title: str
    description: str | None = None
    type: str = "string"
    default: object = None
    options: list[str] | None = None
    option_labels: dict[str, str] | None = None
    minimum: float | None = None
    maximum: float | None = None
    required: bool = False


class ToolSpecRead(BaseModel):
    name: str
    title: str
    description: str
    group: str
    icon: str
    execution: str
    touches_target: bool
    auto: bool
    accepts: list[str] = Field(default_factory=list)
    placeholder: str
    examples: list[str] = Field(default_factory=list)
    fields: list[ToolField] = Field(default_factory=list)


class ToolboxCatalog(BaseModel):
    groups: list[dict] = Field(default_factory=list)
    tools: list[ToolSpecRead] = Field(default_factory=list)


class ToolRunRead(BaseModel):
    id: str
    tool: str
    title: str
    label: str
    input: dict = Field(default_factory=dict)
    status: str
    summary: str | None = None
    blocks: list[Block] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    pivot: Pivot | None = None
    raw: dict | None = None
    error: str | None = None
    queued_at: str
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int | None = None


class ToolRunRequest(BaseModel):
    tool: str
    input: dict = Field(default_factory=dict)
    project_id: str | None = None


class LookupRequest(BaseModel):
    q: str = Field(min_length=1, max_length=MAX_INPUT_LENGTH)
    project_id: str | None = None


class LookupResult(BaseModel):
    kind: str | None = None
    kind_label: str | None = None
    value: str
    runs: list[ToolRunRead] = Field(default_factory=list)
    offered: list[str] = Field(default_factory=list)
    error: str | None = None
