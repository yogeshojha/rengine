import uuid
from datetime import date, datetime

from pydantic import BaseModel
from sqlalchemy import Column, Text
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel, UniqueConstraint

from shared.definitions.threat_intel import FeedStatus
from shared.utils.datetime import utc_now


def _json_list() -> Field:
    return Field(default_factory=list, sa_column=Column(JSON, nullable=False))


class EpssScore(SQLModel, table=True):
    __tablename__ = "epss_scores"

    cve: str = Field(max_length=30, primary_key=True)
    score: float = Field(nullable=False)
    percentile: float = Field(nullable=False)


class KevEntry(SQLModel, table=True):
    __tablename__ = "kev_entries"

    cve: str = Field(max_length=30, primary_key=True)
    vendor: str | None = Field(default=None, max_length=200)
    product: str | None = Field(default=None, max_length=200)
    name: str | None = Field(default=None, max_length=500)
    short_description: str | None = Field(default=None, sa_column=Column(Text))
    required_action: str | None = Field(default=None, sa_column=Column(Text))
    notes: str | None = Field(default=None, sa_column=Column(Text))
    cwes: list = _json_list()
    known_ransomware: bool = Field(default=False, index=True)
    date_added: date | None = Field(default=None, index=True)
    due_date: date | None = Field(default=None)


class CveIntel(SQLModel, table=True):
    """Per-CVE detail fetched from a provider and cached."""

    __tablename__ = "cve_intel"

    cve: str = Field(max_length=30, primary_key=True)
    provider: str = Field(default="vulnx", max_length=32)
    severity: str | None = Field(default=None, max_length=16)
    cvss_score: float | None = Field(default=None)
    description: str | None = Field(default=None, sa_column=Column(Text))
    remediation: str | None = Field(default=None, sa_column=Column(Text))
    weaknesses: list = _json_list()
    pocs: list = _json_list()
    poc_count: int = Field(default=0)
    poc_first_seen: datetime | None = Field(default=None)
    template_available: bool | None = Field(default=None)
    is_remote: bool | None = Field(default=None)
    needs_auth: bool | None = Field(default=None)
    patch_available: bool | None = Field(default=None)
    vendor_kev: bool = Field(default=False)
    kev_sources: list = _json_list()
    exposure_hosts: int | None = Field(default=None)
    exposure_products: list = _json_list()
    hackerone_rank: int | None = Field(default=None)
    hackerone_reports: int | None = Field(default=None)
    published_at: datetime | None = Field(default=None)
    fetched_at: datetime = Field(default_factory=utc_now, index=True)


class ThreatFeed(SQLModel, table=True):
    """One row per feed: what the last refresh did."""

    __tablename__ = "threat_feeds"

    kind: str = Field(max_length=32, primary_key=True)
    status: str = Field(default=FeedStatus.EMPTY.value, max_length=16)
    rows: int = Field(default=0)
    version: str | None = Field(default=None, max_length=100)
    bytes: int = Field(default=0)
    duration_ms: int = Field(default=0)
    error: str | None = Field(default=None, max_length=500)
    last_synced_at: datetime | None = Field(default=None)
    last_attempt_at: datetime | None = Field(default=None)
    updated_at: datetime = Field(default_factory=utc_now)


class IntelSignal(SQLModel, table=True):
    """One reason a finding ranks where it does, with the evidence behind it."""

    __tablename__ = "intel_signals"
    __table_args__ = (
        UniqueConstraint("vulnerability_id", "kind", name="uq_intel_signal_vuln_kind"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    vulnerability_id: uuid.UUID = Field(index=True)
    scan_id: uuid.UUID = Field(foreign_key="scans.id", index=True, ondelete="CASCADE")
    kind: str = Field(max_length=32, index=True)
    weight: int = Field(default=0)
    reason: str = Field(max_length=500)
    evidence: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(default_factory=utc_now)


# ---------- read models ----------


class ThreatFeedRead(BaseModel):
    kind: str
    label: str
    tagline: str
    description: str
    source: str
    source_url: str
    url: str
    license: str
    rows_noun: str = ""
    status: str
    status_label: str
    rows: int
    version: str | None = None
    bytes: int = 0
    duration_ms: int = 0
    error: str | None = None
    last_synced_at: datetime | None = None
    age_hours: float | None = None


class IntelCoverage(BaseModel):
    """How much of the finding set this intelligence actually reaches."""

    findings: int = 0
    with_cve: int = 0
    scored: int = 0
    kev: int = 0
    ransomware: int = 0
    overdue: int = 0
    weaponised: int = 0
    untestable: int = 0
    enriched: int = 0
    bands: dict[str, int] = {}


class IntelChange(BaseModel):
    """A finding whose exploitation intelligence moved on the last refresh."""

    vulnerability_id: uuid.UUID
    scan_id: uuid.UUID
    target_id: uuid.UUID
    target_value: str | None = None
    template_name: str
    severity: str
    cve: str
    host: str | None = None
    matched_at: str | None = None
    change: str
    epss_before: float | None = None
    epss_after: float | None = None
    changed_at: datetime | None = None


class SignalFinding(BaseModel):
    """One finding behind a signal count, with the link that lands on it."""

    vulnerability_id: uuid.UUID
    scan_id: uuid.UUID
    target_id: uuid.UUID
    target_value: str | None = None
    template_name: str
    severity: str
    host: str | None = None
    matched_at: str | None = None
    cve: str = ""
    epss_score: float | None = None
    exploit_score: int = 0
    reason: str = ""


class AutoSyncUpdate(BaseModel):
    enabled: bool


class ThreatIntelStatus(BaseModel):
    auto_sync: bool = True
    feeds: list[ThreatFeedRead]
    coverage: IntelCoverage
    ready: bool
    syncing: bool
    provider_enabled: bool = False
    provider_cached: int = 0
    last_applied_at: datetime | None = None
    recent_changes: list[IntelChange] = []


class SyncResult(BaseModel):
    queued: bool
    feeds: list[str] = []
    detail: str | None = None


class RerankSummary(BaseModel):
    scanned: int = 0
    changed: int = 0
    became_kev: int = 0
    epss_moved: int = 0


class PocRef(BaseModel):
    url: str
    source: str | None = None
    added_at: datetime | None = None


class KevDetail(BaseModel):
    vendor: str | None = None
    product: str | None = None
    name: str | None = None
    short_description: str | None = None
    required_action: str | None = None
    notes: str | None = None
    cwes: list[str] = []
    known_ransomware: bool = False
    date_added: date | None = None
    due_date: date | None = None
    overdue_days: int | None = None


class ExposureProduct(BaseModel):
    id: str
    hosts: int


class CveIntelRead(BaseModel):
    """Everything we know about one CVE: local feeds first, provider detail when cached."""

    cve: str
    epss_score: float | None = None
    epss_percentile: float | None = None
    band: str | None = None
    band_label: str | None = None
    is_kev: bool = False
    kev: KevDetail | None = None
    # provider detail
    enriched: bool = False
    description: str | None = None
    remediation: str | None = None
    weaknesses: list[dict] = []
    pocs: list[PocRef] = []
    poc_count: int = 0
    poc_first_seen: datetime | None = None
    template_available: bool | None = None
    is_remote: bool | None = None
    needs_auth: bool | None = None
    patch_available: bool | None = None
    vendor_kev: bool = False
    exposure_hosts: int | None = None
    exposure_products: list[ExposureProduct] = []
    hackerone_rank: int | None = None
    hackerone_reports: int | None = None
    published_at: datetime | None = None
    fetched_at: datetime | None = None


class SignalRead(BaseModel):
    kind: str
    label: str
    help: str
    tone: str
    weight: int
    reason: str
    evidence: dict = {}


class FindingIntel(BaseModel):
    """The exploitation panel for one finding."""

    exploit_score: int = 0
    signals: list[SignalRead] = []
    cves: list[CveIntelRead] = []
    stale: bool = False
