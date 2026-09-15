import uuid
from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy import Column, Text
from sqlalchemy.types import JSON
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel

from shared.definitions.domain_posture import MAX_ZONE_LENGTH, DnssecState
from shared.utils.datetime import utc_now


class DomainPosture(SQLModel, table=True):
    __tablename__ = "domain_posture"

    id: uuid.UUID = SQLField(default_factory=uuid.uuid4, primary_key=True)
    scan_id: uuid.UUID = SQLField(
        foreign_key="scans.id", index=True, ondelete="CASCADE"
    )
    target_id: uuid.UUID = SQLField(
        foreign_key="targets.id", index=True, ondelete="CASCADE"
    )
    project_id: uuid.UUID = SQLField(foreign_key="projects.id", index=True)

    zone: str = SQLField(max_length=MAX_ZONE_LENGTH, index=True)
    hosts: int = SQLField(default=0)

    spf: str | None = SQLField(default=None, sa_column=Column(Text, nullable=True))
    spf_all: str | None = SQLField(default=None, max_length=16)
    spf_lookups: int | None = SQLField(default=None)
    dmarc: str | None = SQLField(default=None, sa_column=Column(Text, nullable=True))
    dmarc_policy: str | None = SQLField(default=None, max_length=16)
    dmarc_subdomain_policy: str | None = SQLField(default=None, max_length=16)
    dmarc_pct: int | None = SQLField(default=None)
    dmarc_rua: bool | None = SQLField(default=None)
    dkim_selectors: list = SQLField(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    dkim_key_bits: int | None = SQLField(default=None)
    mx: list = SQLField(default_factory=list, sa_column=Column(JSON, nullable=False))
    null_mx: bool = SQLField(default=False)
    mta_sts: str | None = SQLField(default=None, max_length=500)
    mta_sts_mode: str | None = SQLField(default=None, max_length=16)
    tls_rpt: str | None = SQLField(default=None, max_length=500)
    dnssec: str = SQLField(default=DnssecState.UNKNOWN.value, max_length=16)
    caa: list = SQLField(default_factory=list, sa_column=Column(JSON, nullable=False))

    posture_issues: list = SQLField(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    posture_checked: list = SQLField(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    evidence: dict = SQLField(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )

    discovered_at: datetime = SQLField(default_factory=utc_now)
    created_at: datetime = SQLField(default_factory=utc_now)


class DomainPostureRead(BaseModel):
    id: uuid.UUID
    scan_id: uuid.UUID
    target_id: uuid.UUID
    zone: str
    hosts: int = 0
    spf: str | None = None
    spf_all: str | None = None
    spf_lookups: int | None = None
    dmarc: str | None = None
    dmarc_policy: str | None = None
    dmarc_subdomain_policy: str | None = None
    dmarc_pct: int | None = None
    dmarc_rua: bool | None = None
    dkim_selectors: list[str] = Field(default_factory=list)
    dkim_key_bits: int | None = None
    mx: list[str] = Field(default_factory=list)
    null_mx: bool = False
    mta_sts: str | None = None
    mta_sts_mode: str | None = None
    tls_rpt: str | None = None
    dnssec: str
    caa: list[str] = Field(default_factory=list)
    posture_issues: list[str] = Field(default_factory=list)
    posture_checked: list[str] = Field(default_factory=list)
    evidence: dict[str, str] = Field(default_factory=dict)
    discovered_at: datetime


class PostureCheckCount(BaseModel):
    key: str
    failing: int = 0
    applicable: int = 0
    query: str


class DomainPostureSummary(BaseModel):
    """Zones of one scope with the count of each check."""

    covered: bool = False
    scan_id: uuid.UUID | None = None
    target_id: uuid.UUID | None = None
    observed_at: datetime | None = None
    zones: list[DomainPostureRead] = Field(default_factory=list)
    evaluated: int = 0
    clean: int = 0
    warning: int = 0
    info: int = 0
    spoofable: int = 0
    hosts: int = 0
    checks: list[PostureCheckCount] = Field(default_factory=list)
