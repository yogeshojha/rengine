import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from shared.definitions.compare import Comparability


class RunSide(BaseModel):
    """One of the two runs."""

    scan_id: uuid.UUID
    engine_name: str
    context_name: str | None = None
    intensity: str = ""
    scope: str = ""
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    stages_ran: int = 0
    stages_planned: int = 0
    counts: dict[str, int] = Field(default_factory=dict)


class StageDiff(BaseModel):
    name: str
    title: str
    baseline: str | None = None
    current: str | None = None


class SettingDiff(BaseModel):
    stage: str
    title: str
    field: str
    label: str
    before: str | None = None
    after: str | None = None


class RunDifference(BaseModel):
    """One way the two runs were set up differently."""

    key: str
    label: str
    baseline: str | None = None
    current: str | None = None
    material: bool = True


class CoverageLine(BaseModel):
    """One measured account of a run."""

    label: str
    baseline: str | None = None
    current: str | None = None


class DimensionVerdict(BaseModel):
    dimension: str
    comparability: str = Comparability.LIKE_FOR_LIKE.value
    covered_baseline: bool = True
    covered_current: bool = True
    compared: bool = True
    confirmed: bool = True
    note: str = ""
    stages: list[str] = Field(default_factory=list)
    settings: list[SettingDiff] = Field(default_factory=list)
    coverage: list[CoverageLine] = Field(default_factory=list)


class DimensionDelta(BaseModel):
    dimension: str
    label: str
    noun: str
    noun_plural: str
    verdict: DimensionVerdict
    total_baseline: int = 0
    total_current: int = 0
    appeared: int = 0
    changed: int = 0
    disappeared: int = 0
    unconfirmed: int = 0
    unchanged: int = 0
    intel_moved: int = 0

    @property
    def listed(self) -> int:
        return self.appeared + self.changed + self.disappeared + self.unconfirmed


class ChangeField(BaseModel):
    field: str
    label: str
    before: str | None = None
    after: str | None = None
    tone: str = "neutral"


class ScreenshotPair(BaseModel):
    baseline: str | None = None
    current: str | None = None


class ChangeRow(BaseModel):
    key: str
    dimension: str
    verb: str
    signal: str
    rank: int = 99
    title: str
    subtitle: str = ""
    scan_id: uuid.UUID
    fields: list[ChangeField] = Field(default_factory=list)
    severity: str | None = None
    status: int | None = None
    port: int | None = None
    is_kev: bool = False
    sensitive: bool = False
    screenshots: ScreenshotPair | None = None


class ChangeRows(BaseModel):
    dimension: str
    items: list[ChangeRow] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    size: int = 50


class ScanComparison(BaseModel):
    target_id: uuid.UUID
    target_value: str
    target_type: str
    baseline: RunSide
    current: RunSide
    dimensions: list[DimensionDelta] = Field(default_factory=list)
    stage_diff: list[StageDiff] = Field(default_factory=list)
    setting_diff: list[SettingDiff] = Field(default_factory=list)
    settings_identical: int = 0
    run_diff: list[RunDifference] = Field(default_factory=list)
    runs_between: int = 0
    comparability: str = Comparability.LIKE_FOR_LIKE.value
    headline: str = ""
    summary: str = ""
    changes_total: int = 0
    live: bool = False
    suggestion: "ComparableRun | None" = None
    generated_at: datetime


class ComparableRun(BaseModel):
    """A run this one can be put beside."""

    scan_id: uuid.UUID
    engine_name: str
    status: str
    scope: str
    started_at: datetime | None = None
    duration_seconds: float | None = None
    counts: dict[str, int] = Field(default_factory=dict)
    dimensions: list[str] = Field(default_factory=list)
    comparable: bool = True
    reason: str = ""


ScanComparison.model_rebuild()
