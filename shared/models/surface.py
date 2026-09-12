import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SurfaceTargetRead(BaseModel):
    target_id: uuid.UUID
    target_value: str
    target_type: str
    scan_id: uuid.UUID | None = None
    scan_status: str | None = None
    observed_at: datetime | None = None
    stale: bool = False


class SurfaceCoverage(BaseModel):
    dimension: str
    label: str
    noun: str
    noun_plural: str
    total: int = 0
    total_capped: bool = False
    targets_total: int = 0
    targets_covered: int = 0
    observed_from: datetime | None = None
    observed_to: datetime | None = None
    covered: list[SurfaceTargetRead] = Field(default_factory=list)
    uncovered: list[SurfaceTargetRead] = Field(default_factory=list)

    @property
    def stale_targets(self) -> int:
        return sum(1 for row in self.covered if row.stale)


class SurfaceOverview(BaseModel):
    project_id: uuid.UUID
    targets_total: int = 0
    live_scans: int = 0
    exposures: int = 0
    cves: int = 0
    dimensions: list[SurfaceCoverage] = Field(default_factory=list)
    generated_at: datetime
