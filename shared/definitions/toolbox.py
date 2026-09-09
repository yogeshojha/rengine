"""The toolbox vocabulary: how a tool is grouped, where it runs, and how a result is shaped."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


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

GROUP_HELP: dict[str, str] = {
    ToolGroup.LOOKUP.value: "Ask a registry or a resolver what it holds.",
    ToolGroup.DISCOVERY.value: "Find surface that is not in an inventory yet.",
    ToolGroup.INTEL.value: "What is already known about a weakness.",
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
    FACTS = "facts"
    TABLE = "table"
    TAGS = "tags"
    CODE = "code"
    NOTE = "note"


class Tone(StrEnum):
    NEUTRAL = "neutral"
    SUCCESS = "success"
    WARNING = "warning"
    CRITICAL = "critical"
    INFO = "info"
    MUTED = "muted"


RUN_TTL_SECONDS = 7 * 24 * 3600
RUNS_KEPT = 40
RUNS_PER_MINUTE = 30
MAX_INPUT_LENGTH = 500
MAX_ROWS_PER_BLOCK = 2000


class Fact(BaseModel):
    label: str
    value: str
    tone: str = Tone.NEUTRAL.value
    note: str | None = None
    href: str | None = None
    mono: bool = False


class Cell(BaseModel):
    value: str
    tone: str = Tone.NEUTRAL.value
    note: str | None = None
    href: str | None = None
    mono: bool = False
    icon: str | None = None


class Tag(BaseModel):
    value: str
    tone: str = Tone.NEUTRAL.value
    icon: str | None = None
    href: str | None = None
    note: str | None = None


class Block(BaseModel):
    kind: str
    title: str | None = None
    tone: str = Tone.NEUTRAL.value
    facts: list[Fact] = Field(default_factory=list)
    columns: list[str] = Field(default_factory=list)
    rows: list[list[Cell]] = Field(default_factory=list)
    tags: list[Tag] = Field(default_factory=list)
    text: str | None = None
    lang: str | None = None
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
