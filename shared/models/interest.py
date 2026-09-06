import uuid
from datetime import datetime

from pydantic import BaseModel
from pydantic import Field as PField
from sqlalchemy import Column, Index
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel, UniqueConstraint

from shared.definitions.interest import (
    MAX_EVIDENCE,
    MAX_REASON,
    MAX_RULE_NAME,
    InterestBand,
    InterestSource,
    RuleMode,
)
from shared.utils.datetime import utc_now


class InterestRule(SQLModel, table=True):
    __tablename__ = "interest_rules"
    __table_args__ = (
        Index("ix_interest_rules_project_enabled", "project_id", "enabled"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    project_id: uuid.UUID | None = Field(
        default=None, foreign_key="projects.id", index=True, ondelete="CASCADE"
    )
    name: str = Field(max_length=MAX_RULE_NAME)
    description: str | None = Field(default=None, max_length=300)
    mode: str = Field(default=RuleMode.QUERY.value, max_length=16)
    query: str = Field(default="", max_length=2000)
    keywords: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    keyword_fields: list = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    live_only: bool = Field(default=False)
    kind: str = Field(max_length=40)
    weight: int | None = Field(default=None)
    enabled: bool = Field(default=True, index=True)
    builtin: bool = Field(default=False, index=True)
    notify: bool = Field(default=False)
    created_by: uuid.UUID | None = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class InterestSignal(SQLModel, table=True):
    __tablename__ = "interest_signals"
    __table_args__ = (
        UniqueConstraint(
            "scan_id", "subdomain_id", "source", "key", name="uq_interest_signal"
        ),
        Index("ix_interest_signals_scan_score", "scan_id", "weight"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    scan_id: uuid.UUID = Field(foreign_key="scans.id", index=True, ondelete="CASCADE")
    target_id: uuid.UUID = Field(
        foreign_key="targets.id", index=True, ondelete="CASCADE"
    )
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)
    subdomain_id: uuid.UUID = Field(
        foreign_key="subdomains.id", index=True, ondelete="CASCADE"
    )
    host: str = Field(max_length=500, index=True)

    source: str = Field(max_length=16, index=True)
    key: str = Field(max_length=120)
    kind: str = Field(max_length=40, index=True)
    weight: int = Field(default=0)
    label: str = Field(default="", max_length=MAX_RULE_NAME)
    reason: str = Field(default="", max_length=MAX_REASON)
    evidence: str | None = Field(default=None, max_length=MAX_EVIDENCE)
    rule_id: uuid.UUID | None = Field(default=None, index=True)
    model: str | None = Field(default=None, max_length=80)
    prompt_version: str | None = Field(default=None, max_length=16)
    created_at: datetime = Field(default_factory=utc_now)


class InterestDismissal(SQLModel, table=True):
    __tablename__ = "interest_dismissals"
    __table_args__ = (
        UniqueConstraint("target_id", "host", "kind", name="uq_interest_dismissal"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    target_id: uuid.UUID = Field(
        foreign_key="targets.id", index=True, ondelete="CASCADE"
    )
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)
    host: str = Field(max_length=500, index=True)
    kind: str = Field(default="", max_length=40)
    note: str | None = Field(default=None, max_length=300)
    created_by: uuid.UUID | None = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now)


class InterestRuleCreate(BaseModel):
    name: str = PField(min_length=1, max_length=MAX_RULE_NAME)
    description: str | None = None
    mode: str = RuleMode.QUERY.value
    query: str = ""
    keywords: list[str] = PField(default_factory=list)
    keyword_fields: list[str] = PField(default_factory=list)
    live_only: bool = False
    kind: str
    weight: int | None = None
    enabled: bool = True
    notify: bool = False
    project_id: uuid.UUID | None = None


class InterestRuleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    query: str | None = None
    keywords: list[str] | None = None
    keyword_fields: list[str] | None = None
    live_only: bool | None = None
    kind: str | None = None
    weight: int | None = None
    enabled: bool | None = None
    notify: bool | None = None


class InterestRuleRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID | None = None
    name: str
    description: str | None = None
    mode: str
    query: str
    keywords: list[str] = PField(default_factory=list)
    keyword_fields: list[str] = PField(default_factory=list)
    live_only: bool = False
    kind: str
    kind_label: str = ""
    weight: int
    enabled: bool
    builtin: bool
    notify: bool
    updated_at: datetime
    matches: int | None = None
    error: str | None = None


class SignalRead(BaseModel):
    source: str
    kind: str
    kind_label: str
    label: str
    reason: str
    evidence: str | None = None
    weight: int
    rule_id: uuid.UUID | None = None
    model: str | None = None
    judgement: bool = False


class InterestRow(BaseModel):
    subdomain_id: uuid.UUID
    host: str
    score: int
    band: str
    kinds: list[str] = PField(default_factory=list)
    signals: list[SignalRead] = PField(default_factory=list)
    sources: list[str] = PField(default_factory=list)
    http_status: int | None = None
    page_title: str | None = None
    tech: list[str] = PField(default_factory=list)
    webserver: str | None = None
    resolved_ips: list[str] = PField(default_factory=list)
    asn: int | None = None
    asn_org: str | None = None
    is_cdn: bool = False
    screenshot_path: str | None = None
    is_new: bool = False
    dismissed: bool = False


class InterestSummary(BaseModel):
    total: int = 0
    bands: dict[str, int] = PField(default_factory=dict)
    sources: dict[str, int] = PField(default_factory=dict)
    kinds: dict[str, int] = PField(default_factory=dict)
    dismissed: int = 0
    judged_hosts: int = 0
    judged_at: datetime | None = None
    model: str | None = None
    ai_available: bool = False
    ai_enabled: bool = False
    stale: bool = False


class InterestFilter(BaseModel):
    q: str | None = PField(default=None, max_length=200)
    bands: list[str] = PField(default_factory=list, max_length=8)
    sources: list[str] = PField(default_factory=list, max_length=8)
    kinds: list[str] = PField(default_factory=list, max_length=40)
    sort: str = "score"
    order: str = "desc"
    limit: int = PField(default=50, ge=1, le=200)
    offset: int = PField(default=0, ge=0, le=100_000)


class InterestPage(BaseModel):
    rows: list[InterestRow] = PField(default_factory=list)
    total: int = 0
    summary: InterestSummary = PField(default_factory=InterestSummary)


class KindEntry(BaseModel):
    key: str
    label: str
    help: str
    weight: int
    tone: str


class SourceEntry(BaseModel):
    key: str
    label: str
    help: str
    judgement: bool = False


class BandEntry(BaseModel):
    key: str
    label: str
    tone: str
    floor: int


class InterestCatalog(BaseModel):
    kinds: list[KindEntry] = PField(default_factory=list)
    sources: list[SourceEntry] = PField(default_factory=list)
    bands: list[BandEntry] = PField(default_factory=list)
    modes: dict[str, str] = PField(default_factory=dict)
    keyword_fields: dict[str, str] = PField(default_factory=dict)
    max_score: int = 0
    providers: list[str] = PField(default_factory=list)


class RulePreview(BaseModel):
    matches: int = 0
    capped: bool = False
    error: str | None = None
    sample: list[str] = PField(default_factory=list)


class RuleSuggestion(BaseModel):
    name: str
    kind: str
    kind_label: str = ""
    query: str
    reason: str = ""
    matches: int = 0


class DismissRequest(BaseModel):
    host: str = PField(min_length=1, max_length=500)
    target_id: uuid.UUID
    kind: str = ""
    note: str | None = None


class JudgeRequest(BaseModel):
    force: bool = False


DEFAULT_BAND = InterestBand.NOTABLE.value
DEFAULT_SOURCE = InterestSource.RULE.value
