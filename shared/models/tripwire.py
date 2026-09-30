import uuid
from datetime import datetime
from functools import partial
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from pydantic import Field as PField
from sqlalchemy import Column, Index, PrimaryKeyConstraint
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel, UniqueConstraint

from shared.definitions.asset_query import MAX_QUERY_LENGTH
from shared.definitions.surface import SURFACE_ORDER
from shared.definitions.tripwires import (
    MAX_ACTIONS,
    MAX_CHANNELS,
    MAX_NAME,
    MAX_SCOPE_IDS,
    MAX_STAGES,
    ActionKind,
    FireOn,
    ScopeKind,
    Trigger,
)
from shared.models.asset_query import QueryError
from shared.utils.datetime import utc_now
from shared.utils.validation import clean_name, clean_optional_name


class Tripwire(SQLModel, table=True):
    __tablename__ = "tripwires"
    __table_args__ = (Index("ix_tripwires_project_enabled", "project_id", "enabled"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(
        foreign_key="projects.id", index=True, ondelete="CASCADE"
    )
    name: str = Field(max_length=MAX_NAME)
    dimension: str = Field(max_length=32)
    query: str = Field(default="", max_length=MAX_QUERY_LENGTH)
    trigger: str = Field(default=Trigger.SCAN_SETTLED.value, max_length=16)
    fire_on: str = Field(default=FireOn.APPEARS.value, max_length=16)
    scope_kind: str = Field(default=ScopeKind.ALL.value, max_length=16)
    scope_ids: list = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    actions: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    enabled: bool = Field(default=True)
    fired_count: int = Field(default=0)
    last_fired_at: datetime | None = Field(default=None)
    last_checked_at: datetime | None = Field(default=None)
    created_by: uuid.UUID | None = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class TripwireRun(SQLModel, table=True):
    """One check of one tripwire against one scan."""

    __tablename__ = "tripwire_runs"
    __table_args__ = (
        UniqueConstraint("tripwire_id", "scan_id", name="uq_tripwire_run"),
        Index("ix_tripwire_runs_tripwire_checked", "tripwire_id", "checked_at"),
        Index("ix_tripwire_runs_project_fired", "project_id", "fired_at"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tripwire_id: uuid.UUID = Field(
        foreign_key="tripwires.id", index=True, ondelete="CASCADE"
    )
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)
    target_id: uuid.UUID = Field(
        foreign_key="targets.id", index=True, ondelete="CASCADE"
    )
    scan_id: uuid.UUID = Field(foreign_key="scans.id", index=True, ondelete="CASCADE")
    status: str = Field(max_length=16, index=True)
    matched: int = Field(default=0)
    fired: int = Field(default=0)
    rows: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    outcomes: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    detail: str | None = Field(default=None, max_length=500)
    checked_at: datetime = Field(default_factory=utc_now)
    fired_at: datetime | None = Field(default=None)


class TripwireMark(SQLModel, table=True):
    """A row a tripwire fired on during a scan."""

    __tablename__ = "tripwire_marks"
    __table_args__ = (PrimaryKeyConstraint("tripwire_id", "scan_id", "key"),)

    tripwire_id: uuid.UUID = Field(foreign_key="tripwires.id", ondelete="CASCADE")
    scan_id: uuid.UUID = Field(foreign_key="scans.id", index=True, ondelete="CASCADE")
    key: str = Field(max_length=600)
    marked_at: datetime = Field(default_factory=utc_now)


# ---------- actions ----------


class NotifyAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["notify"] = ActionKind.NOTIFY.value
    channel_ids: list[uuid.UUID] = PField(default_factory=list, max_length=MAX_CHANNELS)


class ScanAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["scan"] = ActionKind.SCAN.value
    stages: list[str] = PField(default_factory=list, max_length=MAX_STAGES)
    intensity: str | None = PField(default=None, max_length=16)


TripwireAction = Annotated[NotifyAction | ScanAction, PField(discriminator="kind")]


class TripwireScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = ScopeKind.ALL.value
    ids: list[uuid.UUID] = PField(default_factory=list, max_length=MAX_SCOPE_IDS)

    @model_validator(mode="after")
    def _shape(self):
        if self.kind not in {k.value for k in ScopeKind}:
            msg = f"Unknown scope '{self.kind}'."
            raise ValueError(msg)
        if self.kind == ScopeKind.ALL.value:
            self.ids = []
        elif not self.ids:
            msg = "Choose at least one target, organization or tag."
            raise ValueError(msg)
        elif self.kind != ScopeKind.TARGETS.value and len(self.ids) != 1:
            msg = "An organization or tag scope takes one id."
            raise ValueError(msg)
        return self


class TripwireScopeRead(TripwireScope):
    labels: list[str] = PField(default_factory=list)


def _known_dimension(value: str) -> str:
    if value not in SURFACE_ORDER:
        msg = f"Unknown dimension '{value}'."
        raise ValueError(msg)
    return value


def _known(enum, noun: str):
    values = {member.value for member in enum}

    def check(value: str) -> str:
        if value not in values:
            msg = f"Unknown {noun} '{value}'."
            raise ValueError(msg)
        return value

    return check


def _some_query(value: str) -> str:
    text = (value or "").strip()
    if not text:
        msg = "A query is required."
        raise ValueError(msg)
    return text


class TripwireCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = PField(max_length=MAX_NAME)
    dimension: str = PField(max_length=32)
    query: str = PField(max_length=MAX_QUERY_LENGTH)
    trigger: str = Trigger.SCAN_SETTLED.value
    fire_on: str = FireOn.APPEARS.value
    scope: TripwireScope = PField(default_factory=TripwireScope)
    actions: list[TripwireAction] = PField(default_factory=list, max_length=MAX_ACTIONS)
    enabled: bool = True

    _validate_name = field_validator("name")(partial(clean_name, max_len=MAX_NAME))
    _validate_dimension = field_validator("dimension")(_known_dimension)
    _validate_query = field_validator("query")(_some_query)
    _validate_trigger = field_validator("trigger")(_known(Trigger, "trigger"))
    _validate_fire_on = field_validator("fire_on")(_known(FireOn, "fire mode"))

    @field_validator("actions")
    @classmethod
    def _one_of_each(cls, actions):
        kinds = [a.kind for a in actions]
        if len(kinds) != len(set(kinds)):
            msg = "One action of each kind."
            raise ValueError(msg)
        return actions


class TripwireUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = PField(default=None, max_length=MAX_NAME)
    dimension: str | None = PField(default=None, max_length=32)
    query: str | None = PField(default=None, max_length=MAX_QUERY_LENGTH)
    trigger: str | None = None
    fire_on: str | None = None
    scope: TripwireScope | None = None
    actions: list[TripwireAction] | None = PField(default=None, max_length=MAX_ACTIONS)
    enabled: bool | None = None

    _validate_name = field_validator("name")(
        partial(clean_optional_name, max_len=MAX_NAME)
    )

    @field_validator("dimension")
    @classmethod
    def _dimension(cls, value):
        return None if value is None else _known_dimension(value)

    @field_validator("query")
    @classmethod
    def _query(cls, value):
        return None if value is None else _some_query(value)

    @field_validator("trigger")
    @classmethod
    def _trigger(cls, value):
        return None if value is None else _known(Trigger, "trigger")(value)

    @field_validator("fire_on")
    @classmethod
    def _fire_on(cls, value):
        return None if value is None else _known(FireOn, "fire mode")(value)

    @field_validator("actions")
    @classmethod
    def _one_of_each(cls, actions):
        if actions is None:
            return None
        kinds = [a.kind for a in actions]
        if len(kinds) != len(set(kinds)):
            msg = "One action of each kind."
            raise ValueError(msg)
        return actions


class TripwireRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    dimension: str
    query: str
    trigger: str
    fire_on: str
    scope: TripwireScopeRead
    actions: list[TripwireAction] = PField(default_factory=list)
    enabled: bool
    fired_count: int = 0
    recent_fired: int = 0
    last_fired_at: datetime | None = None
    last_checked_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


# ---------- checks ----------


class FiredRow(BaseModel):
    key: str
    label: str
    detail: str = ""
    severity: str | None = None
    seed: str | None = None


class Outcome(BaseModel):
    kind: str
    status: str
    detail: str = ""
    scan_id: uuid.UUID | None = None


class TripwireRunRead(BaseModel):
    id: uuid.UUID
    tripwire_id: uuid.UUID
    target_id: uuid.UUID
    target_value: str = ""
    scan_id: uuid.UUID
    status: str
    matched: int
    fired: int
    rows: list[FiredRow] = PField(default_factory=list)
    outcomes: list[Outcome] = PField(default_factory=list)
    detail: str | None = None
    checked_at: datetime
    fired_at: datetime | None = None


class TripwireRunCounts(BaseModel):
    fired: int = 0
    quiet: int = 0
    total: int = 0


# ---------- preview ----------


class TripwirePreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimension: str = PField(max_length=32)
    query: str = PField(default="", max_length=MAX_QUERY_LENGTH)
    fire_on: str = FireOn.APPEARS.value
    scope: TripwireScope = PField(default_factory=TripwireScope)

    _validate_dimension = field_validator("dimension")(_known_dimension)
    _validate_fire_on = field_validator("fire_on")(_known(FireOn, "fire mode"))


class PreviewTarget(BaseModel):
    target_id: uuid.UUID
    target_value: str
    scan_id: uuid.UUID
    status: str
    matched: int
    fired: int
    capped: bool = False
    completed_at: datetime | None = None


class TripwirePreview(BaseModel):
    """What would fire on the latest settled run of each target in scope."""

    targets: list[PreviewTarget] = PField(default_factory=list)
    matched: int = 0
    fired: int = 0
    rows: list[FiredRow] = PField(default_factory=list)
    unscanned: int = 0
    capped: bool = False
    error: QueryError | None = None


class TripwireBacktest(BaseModel):
    """What would have fired on the settled runs of the last days."""

    days: int
    runs: list[PreviewTarget] = PField(default_factory=list)
    capped: bool = False
    error: QueryError | None = None


# ---------- catalog ----------


class ChoiceSpec(BaseModel):
    key: str
    label: str
    help: str = ""


class TemplateRead(BaseModel):
    key: str
    name: str
    dimension: str
    query: str
    fire_on: str
    trigger: str
    group: str


class TripwireDimension(BaseModel):
    key: str
    label: str
    noun: str
    noun_plural: str
    stages: list[str] = PField(default_factory=list)
    default_stages: list[str] = PField(default_factory=list)


class StageChoice(BaseModel):
    name: str
    title: str


class ChannelChoice(BaseModel):
    id: uuid.UUID
    name: str
    provider: str


class TripwireCatalog(BaseModel):
    dimensions: list[TripwireDimension] = PField(default_factory=list)
    triggers: list[ChoiceSpec] = PField(default_factory=list)
    fire_modes: list[ChoiceSpec] = PField(default_factory=list)
    actions: list[ChoiceSpec] = PField(default_factory=list)
    stages: list[StageChoice] = PField(default_factory=list)
    templates: list[TemplateRead] = PField(default_factory=list)
    template_groups: list[ChoiceSpec] = PField(default_factory=list)
    channels: list[ChannelChoice] = PField(default_factory=list)
    max_tripwires: int
    max_runs_per_day: int
    recent_days: int
