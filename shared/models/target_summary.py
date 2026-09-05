import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from shared.models.scan import ScanRead
from shared.models.vulnerability import SeverityCount


class SurfaceMetric(BaseModel):
    """What the most recent scan that actually ran this dimension found."""

    key: str
    label: str
    covered: bool = False
    value: int | None = None
    previous: int | None = None
    delta: int | None = None
    added: int | None = None
    gone: int | None = None
    scan_id: uuid.UUID | None = None
    scan_status: str | None = None
    observed_at: datetime | None = None
    current: bool = False


class TargetRisk(BaseModel):
    scan_id: uuid.UUID | None = None
    observed_at: datetime | None = None
    total: int = 0
    actionable: int = 0
    kev: int = 0
    suppressed: int = 0
    by_severity: list[SeverityCount] = Field(default_factory=list)


class TargetMonitoring(BaseModel):
    schedule_id: uuid.UUID
    name: str
    cadence: str
    status: str
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None


class TargetSummaryRead(BaseModel):
    target_id: uuid.UUID
    scans_total: int = 0
    scans_running: int = 0
    scans_failed: int = 0
    first_scan_at: datetime | None = None
    last_scan_at: datetime | None = None
    last_completed_at: datetime | None = None
    latest_scan: ScanRead | None = None
    surface: list[SurfaceMetric] = Field(default_factory=list)
    risk: TargetRisk = Field(default_factory=TargetRisk)
    sensitive_services: int | None = None
    inventory_total: int = 0
    inventory_first_seen: datetime | None = None
    monitoring: TargetMonitoring | None = None
