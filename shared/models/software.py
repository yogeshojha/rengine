import uuid
from datetime import date, datetime

from pydantic import BaseModel
from sqlalchemy import BigInteger, Column, Text
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel, UniqueConstraint

from shared.definitions.software import Confidence, VersionSource
from shared.definitions.vulnerabilities import Severity
from shared.models.asset_query import QueryError
from shared.utils.datetime import utc_now


def _json_list() -> Field:
    return Field(default_factory=list, sa_column=Column(JSON, nullable=False))


class NvdCve(SQLModel, table=True):
    """One published CVE, as NVD states it."""

    __tablename__ = "nvd_cves"

    cve: str = Field(max_length=30, primary_key=True)
    severity: str | None = Field(default=None, max_length=16, index=True)
    cvss_score: float | None = Field(default=None)
    cvss_vector: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, sa_column=Column(Text))
    published_at: datetime | None = Field(default=None, index=True)
    last_modified_at: datetime | None = Field(default=None)


class NvdCpeMatch(SQLModel, table=True):
    """One version range NVD states a CVE applies to."""

    __tablename__ = "nvd_cpe_matches"

    id: int | None = Field(
        default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    cve: str = Field(max_length=30, index=True)
    vendor: str = Field(max_length=200)
    product: str = Field(max_length=200, index=True)
    version_kind: str = Field(max_length=1)
    exact_key: str | None = Field(default=None, max_length=160)
    start_key: str | None = Field(default=None, max_length=160)
    start_incl: bool = Field(default=False)
    end_key: str | None = Field(default=None, max_length=160)
    end_incl: bool = Field(default=False)
    conditional: bool = Field(default=False)


class SoftwareCve(SQLModel, table=True):
    """A CVE inferred from the version an asset reports. Nothing was sent to confirm it."""

    __tablename__ = "software_cves"
    __table_args__ = (
        UniqueConstraint("scan_id", "fingerprint", name="uq_software_scan_fingerprint"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    scan_id: uuid.UUID = Field(foreign_key="scans.id", index=True, ondelete="CASCADE")
    target_id: uuid.UUID = Field(
        foreign_key="targets.id", index=True, ondelete="CASCADE"
    )
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)

    fingerprint: str = Field(max_length=64, index=True)
    cve: str = Field(max_length=30, index=True)

    # what it runs
    name: str = Field(max_length=120, index=True)
    version: str = Field(max_length=64)
    vendor: str = Field(max_length=200)
    product: str = Field(max_length=200, index=True)
    cpe: str = Field(max_length=300)
    version_source: str = Field(default=VersionSource.BANNER.value, max_length=16)

    # what it is worth
    severity: str = Field(default=Severity.UNKNOWN.value, max_length=16, index=True)
    cvss_score: float | None = Field(default=None)
    epss_score: float | None = Field(default=None)
    epss_percentile: float | None = Field(default=None)
    is_kev: bool = Field(default=False, index=True)
    kev_ransomware: bool = Field(default=False)
    kev_due_date: date | None = Field(default=None)
    exploit_score: int = Field(default=0, index=True)
    intel_kinds: list = _json_list()
    confidence: str = Field(default=Confidence.HIGH.value, max_length=16, index=True)
    caveats: list = _json_list()

    # where it is
    host: str | None = Field(default=None, max_length=500, index=True)
    ip: str | None = Field(default=None, max_length=45, index=True)
    port: int | None = Field(default=None, index=True)
    url: str | None = Field(default=None, max_length=2000)
    http_asset_id: uuid.UUID | None = Field(default=None, index=True)
    port_id: uuid.UUID | None = Field(default=None, index=True)

    discovered_at: datetime = Field(default_factory=utc_now, index=True)
    created_at: datetime = Field(default_factory=utc_now)


# ---------- read models ----------


class SoftwareCveRead(BaseModel):
    id: uuid.UUID
    scan_id: uuid.UUID
    target_id: uuid.UUID
    target_value: str | None = None
    cve: str
    name: str
    version: str
    vendor: str
    product: str
    cpe: str
    version_source: str
    version_source_label: str
    severity: str
    cvss_score: float | None = None
    epss_score: float | None = None
    epss_percentile: float | None = None
    band: str | None = None
    is_kev: bool = False
    kev_ransomware: bool = False
    kev_due_date: date | None = None
    exploit_score: int = 0
    intel_kinds: list[str] = []
    confidence: str
    confidence_label: str
    caveats: list[dict] = []
    description: str | None = None
    host: str | None = None
    ip: str | None = None
    port: int | None = None
    url: str | None = None
    http_asset_id: uuid.UUID | None = None
    port_id: uuid.UUID | None = None
    discovered_at: datetime
    is_new: bool = False


class SoftwareComponentRead(BaseModel):
    """One piece of software an asset reports, and whether it could be looked up."""

    name: str
    version: str | None = None
    vendor: str | None = None
    product: str | None = None
    version_source: str
    mapped: bool = False
    cves: int = 0
    assets: int = 0


class SoftwareCoverage(BaseModel):
    """What the inference reached, and what it could not."""

    components: int = 0
    mapped: int = 0
    unmapped: int = 0
    matched: int = 0
    findings: int = 0
    feed_ready: bool = False
    feed_age_hours: float | None = None
    stale: bool = False
    unmapped_names: list[SoftwareComponentRead] = []


class SoftwareFacet(BaseModel):
    key: str
    label: str
    count: int = 0


class SoftwareFacets(BaseModel):
    severity: list[SoftwareFacet] = []
    confidence: list[SoftwareFacet] = []
    source: list[SoftwareFacet] = []
    caveat: list[SoftwareFacet] = []
    product: list[SoftwareFacet] = []


class SoftwarePage(BaseModel):
    items: list[SoftwareCveRead] = []
    total: int = 0
    total_capped: bool = False
    error: QueryError | None = None


class SoftwareFilter(BaseModel):
    q: str | None = None
    limit: int = 50
    offset: int = 0
    sort: str | None = None
    direction: str | None = None
