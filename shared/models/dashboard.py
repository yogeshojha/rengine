import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from shared.models.vulnerability import SeverityCount


class TakeoverCandidate(BaseModel):
    name: str
    target_id: uuid.UUID
    cname: str
    provider: str
    last_seen: datetime


class TakeoverSignal(BaseModel):
    count: int
    items: list[TakeoverCandidate] = Field(default_factory=list)


class SpoofableDomain(BaseModel):
    target_id: uuid.UUID
    target_value: str
    zone: str = ""
    reason: str
    check: str = ""


class SpoofableSignal(BaseModel):
    count: int
    items: list[SpoofableDomain] = Field(default_factory=list)


class StaleTarget(BaseModel):
    target_id: uuid.UUID
    target_value: str
    target_type: str
    last_scanned_at: datetime | None = None


class StaleSignal(BaseModel):
    never_scanned: int
    stale: int
    items: list[StaleTarget] = Field(default_factory=list)


class DashboardSignals(BaseModel):
    takeover: TakeoverSignal
    spoofable: SpoofableSignal
    stale: StaleSignal


class DashboardTargetCount(BaseModel):
    target_id: uuid.UUID
    target_value: str
    scan_id: uuid.UUID
    count: int


class ExpiringTarget(BaseModel):
    target_id: uuid.UUID
    target_value: str
    expires_at: datetime


class FailedRun(BaseModel):
    target_id: uuid.UUID
    target_value: str
    scan_id: uuid.UUID
    engine_name: str
    error: str | None = None
    at: datetime


class DashboardSurfaceMetric(BaseModel):
    key: str
    label: str
    value: int = 0
    targets_covered: int = 0
    new_in_window: int = 0


class DashboardEvidenceCell(BaseModel):
    severity: str
    evidence: str
    count: int = 0


class DashboardFinding(BaseModel):
    id: uuid.UUID
    scan_id: uuid.UUID
    target_id: uuid.UUID
    target_value: str
    template_id: str
    name: str
    severity: str
    host: str | None = None
    matched_at: str
    host_count: int = 1
    is_kev: bool = False
    is_new: bool = False
    cve_ids: list[str] = Field(default_factory=list)
    epss_score: float | None = None
    cvss_score: float | None = None
    discovered_at: datetime
    evidence: str | None = None
    tier: str = "track"
    replays: int = 0


class DashboardRisk(BaseModel):
    total: int = 0
    actionable: int = 0
    kev: int = 0
    ransomware: int = 0
    overdue: int = 0
    newly_exploited: int = 0
    new_in_window: int = 0
    suppressed: int = 0
    targets_affected: int = 0
    targets_scanned: int = 0
    by_severity: list[SeverityCount] = Field(default_factory=list)
    evidence: list[DashboardEvidenceCell] = Field(default_factory=list)
    tiers: dict[str, int] = Field(default_factory=dict)
    queue: list[DashboardFinding] = Field(default_factory=list)


class DashboardGeo(BaseModel):
    code: str
    count: int
    targets: list[DashboardTargetCount] = Field(default_factory=list)


class DashboardExposureBand(BaseModel):
    key: str
    label: str
    count: int = 0
    targets: int = 0
    query: str


class DashboardExposedService(BaseModel):
    key: str
    label: str
    service_class: str
    sensitive: bool = False
    count: int = 0
    query: str
    targets: list[DashboardTargetCount] = Field(default_factory=list)


class DashboardExposure(BaseModel):
    services: int = 0
    addresses: int = 0
    targets: int = 0
    sensitive: int = 0
    sensitive_targets: int = 0
    non_web: int = 0
    bands: list[DashboardExposureBand] = Field(default_factory=list)
    top: list[DashboardExposedService] = Field(default_factory=list)


class DashboardCertBucket(BaseModel):
    key: str
    label: str
    count: int = 0
    query: str


class DashboardCertSignal(BaseModel):
    count: int = 0
    query: str
    targets: list[DashboardTargetCount] = Field(default_factory=list)


class DashboardCerts(BaseModel):
    expired: DashboardCertSignal
    expiring: DashboardCertSignal
    buckets: list[DashboardCertBucket] = Field(default_factory=list)


class DashboardChangeRow(BaseModel):
    target_id: uuid.UUID
    target_value: str
    target_type: str
    runs: int = 0
    last_scan_id: uuid.UUID
    last_status: str
    last_at: datetime
    new: dict[str, int] = Field(default_factory=dict)
    new_scan: dict[str, uuid.UUID | None] = Field(default_factory=dict)
    first: list[str] = Field(default_factory=list)
    gone_web_assets: int = 0


class DashboardDay(BaseModel):
    date: str
    runs: int = 0
    failed: int = 0
    outcomes: dict[str, int] = Field(default_factory=dict)
    new: dict[str, int] = Field(default_factory=dict)
    retired: dict[str, int] = Field(default_factory=dict)
    total: dict[str, int] = Field(default_factory=dict)
    findings: dict[str, int] = Field(default_factory=dict)


class DashboardFunnelStep(BaseModel):
    key: str
    label: str
    count: int = 0
    new_in_window: int | None = None
    query: str | None = None
    tab: str | None = None


class DashboardFunnel(BaseModel):
    steps: list[DashboardFunnelStep] = Field(default_factory=list)


class DashboardTargetRow(BaseModel):
    id: uuid.UUID
    value: str
    monitored: bool = False


class DashboardReadiness(BaseModel):
    worker_online: bool = False
    worker_concurrency: int | None = None
    checks_ready: bool = False
    checks_total: int = 0


class DashboardOverview(BaseModel):
    generated_at: datetime
    window: str
    first_run: bool = False
    targets_total: int = 0
    targets_scanned: int = 0
    targets_never_scanned: int = 0
    targets_stale: int = 0
    targets_monitored: int = 0
    targets_by_type: dict[str, int] = Field(default_factory=dict)
    runs_total: int = 0
    runs_in_window: int = 0
    failed_in_window: int = 0
    last_completed_at: datetime | None = None
    surface: list[DashboardSurfaceMetric] = Field(default_factory=list)
    funnel: DashboardFunnel = Field(default_factory=DashboardFunnel)
    risk: DashboardRisk = Field(default_factory=DashboardRisk)
    signals: DashboardSignals
    never_scanned: list[StaleTarget] = Field(default_factory=list)
    stale: list[StaleTarget] = Field(default_factory=list)
    sensitive: list[DashboardTargetCount] = Field(default_factory=list)
    expiring: list[ExpiringTarget] = Field(default_factory=list)
    failed_runs: list[FailedRun] = Field(default_factory=list)
    exposure: DashboardExposure = Field(default_factory=DashboardExposure)
    certs: DashboardCerts
    geography: list[DashboardGeo] = Field(default_factory=list)
    geo_total: int = 0
    changes: list[DashboardChangeRow] = Field(default_factory=list)
    daily: list[DashboardDay] = Field(default_factory=list)
    targets: list[DashboardTargetRow] = Field(default_factory=list)


class DashboardDiscoverySource(BaseModel):
    target_id: uuid.UUID
    target_value: str
    scan_id: uuid.UUID
    seen_on: str
    hostname_count: int = 0


class DashboardDiscoveredDomain(BaseModel):
    domain: str
    hostname_count: int = 0
    hostnames: list[str] = Field(default_factory=list)
    sources: list[DashboardDiscoverySource] = Field(default_factory=list)


class DashboardDiscovery(BaseModel):
    targets_examined: int = 0
    domains: list[DashboardDiscoveredDomain] = Field(default_factory=list)


class DashboardEvent(BaseModel):
    at: datetime
    kind: str
    label: str
    title: str
    detail: str | None = None
    tone: str = "neutral"
    scan_id: uuid.UUID | None = None
    target_id: uuid.UUID | None = None
    watch_id: uuid.UUID | None = None
    platform: str | None = None
    handle: str | None = None
    connector_id: uuid.UUID | None = None


class DashboardActivity(BaseModel):
    window: str
    events: list[DashboardEvent] = Field(default_factory=list)


class DashboardDayKinds(BaseModel):
    date: str
    kinds: dict[str, int] = Field(default_factory=dict)


class DashboardWatchAlert(BaseModel):
    watch_id: uuid.UUID
    name: str
    program_name: str
    at: datetime


class DashboardLadderStep(BaseModel):
    state: str
    label: str
    count: int = 0


class DashboardWatches(BaseModel):
    total: int = 0
    active: int = 0
    daily: list[DashboardDayKinds] = Field(default_factory=list)
    ladder: list[DashboardLadderStep] = Field(default_factory=list)
    latest_alert: DashboardWatchAlert | None = None
    stream_running: bool = False
    stream_certificates: int = 0
    last_certificate_at: datetime | None = None


class DashboardBrowsing(BaseModel):
    connectors: int = 0
    live: int = 0
    requests_seen: int = 0
    browsed: int = 0
    unseen: int = 0
    new_params: int = 0
    flagged: int = 0
    last_seen_at: datetime | None = None
    daily: list[DashboardDayKinds] = Field(default_factory=list)


class DashboardPrograms(BaseModel):
    window: str
    programs_total: int = 0
    by_platform: dict[str, int] = Field(default_factory=dict)
    watched: int = 0
    events_in_window: dict[str, int] = Field(default_factory=dict)
    events_daily: list[DashboardDayKinds] = Field(default_factory=list)
    watches: DashboardWatches = Field(default_factory=DashboardWatches)
    browsing: DashboardBrowsing = Field(default_factory=DashboardBrowsing)


class SurfaceRiskTarget(BaseModel):
    target_id: uuid.UUID
    target_value: str
    target_type: str
    names: int = 0
    live: int = 0
    findings: int = 0
    actionable: int = 0
    act: int = 0
    kev: int = 0
    by_severity: dict[str, int] = Field(default_factory=dict)
    scan_id: uuid.UUID | None = None
    scan_status: str | None = None
    last_at: datetime | None = None
    organizations: list[uuid.UUID] = Field(default_factory=list)
    tags: list[uuid.UUID] = Field(default_factory=list)


class DashboardSurfaceRisk(BaseModel):
    targets_total: int = 0
    scanned: int = 0
    live: int = 0
    findings: int = 0
    actionable: int = 0
    act: int = 0
    rows: list[SurfaceRiskTarget] = Field(default_factory=list)
