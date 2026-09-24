import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel
from sqlalchemy import Column, Numeric
from sqlmodel import Field, SQLModel, UniqueConstraint

from shared.definitions.bounty_reports import (
    MAX_CURRENCY,
    MAX_REPORT_TITLE,
    MAX_WEAKNESS,
)
from shared.utils.datetime import utc_now


class BountyReport(SQLModel, table=True):
    __tablename__ = "bounty_reports"
    __table_args__ = (
        UniqueConstraint("platform", "external_id", name="uq_bounty_report_external"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    platform: str = Field(max_length=32, index=True)
    external_id: str = Field(max_length=100)
    program_handle: str | None = Field(default=None, max_length=200, index=True)
    title: str = Field(max_length=MAX_REPORT_TITLE)
    state: str = Field(max_length=32, index=True)
    severity: str | None = Field(default=None, max_length=16, index=True)
    severity_score: float | None = Field(default=None)
    weakness: str | None = Field(default=None, max_length=MAX_WEAKNESS)
    asset_type: str | None = Field(default=None, max_length=48)
    asset_identifier: str | None = Field(default=None, max_length=1000)
    submitted_at: datetime | None = Field(default=None, index=True)
    triaged_at: datetime | None = Field(default=None)
    closed_at: datetime | None = Field(default=None)
    bounty_awarded_at: datetime | None = Field(default=None)
    disclosed_at: datetime | None = Field(default=None)
    last_program_activity_at: datetime | None = Field(default=None)
    synced_at: datetime = Field(default_factory=utc_now)


class BountyAward(SQLModel, table=True):
    __tablename__ = "bounty_awards"
    __table_args__ = (
        UniqueConstraint("platform", "external_id", name="uq_bounty_award_external"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    platform: str = Field(max_length=32, index=True)
    external_id: str = Field(max_length=100)
    report_external_id: str | None = Field(default=None, max_length=100, index=True)
    program_handle: str | None = Field(default=None, max_length=200, index=True)
    program_name: str | None = Field(default=None, max_length=300)
    amount: Decimal = Field(sa_column=Column(Numeric(14, 2), nullable=False))
    bonus: Decimal = Field(
        default=Decimal(0), sa_column=Column(Numeric(14, 2), nullable=False)
    )
    currency: str = Field(max_length=MAX_CURRENCY)
    awarded_at: datetime | None = Field(default=None, index=True)
    synced_at: datetime = Field(default_factory=utc_now)


class BountyAccount(SQLModel, table=True):
    __tablename__ = "bounty_accounts"

    platform: str = Field(max_length=32, primary_key=True)
    username: str | None = Field(default=None, max_length=200)
    reputation: int | None = Field(default=None)
    signal: float | None = Field(default=None)
    impact: float | None = Field(default=None)
    synced_at: datetime | None = Field(default=None)
    error: str | None = Field(default=None, max_length=500)


class Money(BaseModel):
    currency: str
    amount: float
    awards: int


class ReportStateCount(BaseModel):
    state: str
    label: str
    stage: str
    count: int


class SeverityCount(BaseModel):
    severity: str
    count: int


class MonthPoint(BaseModel):
    month: str
    open: int = 0
    resolved: int = 0
    closed: int = 0
    earned: float = 0.0
    awards: int = 0


class AwardRead(BaseModel):
    amount: float
    bonus: float
    currency: str
    awarded_at: datetime | None


class ProgramReports(BaseModel):
    handle: str
    name: str
    in_hub: bool
    reports: int
    open: int
    resolved: int
    closed: int
    critical: int
    high: int
    paid_reports: int
    earned: list[Money] = []
    first_submitted_at: datetime | None
    last_submitted_at: datetime | None


class BountyAccountSummary(BaseModel):
    platform: str
    label: str
    url: str
    username: str | None
    reputation: int | None
    signal: float | None
    impact: float | None
    synced_at: datetime | None
    error: str | None
    reports: int
    programs: int
    stages: dict[str, int]
    states: list[ReportStateCount]
    severities: list[SeverityCount]
    earned: list[Money]
    paid_reports: int
    first_submitted_at: datetime | None
    last_submitted_at: datetime | None
    monthly: list[MonthPoint] = []
    chart_currency: str | None = None


class BountyReportRead(BaseModel):
    id: uuid.UUID
    platform: str
    external_id: str
    url: str = ""
    program_handle: str | None
    program_name: str | None = None
    program_in_hub: bool = False
    title: str
    state: str
    state_label: str = ""
    stage: str = ""
    severity: str | None
    severity_score: float | None
    weakness: str | None
    asset_type: str | None = None
    asset_identifier: str | None
    submitted_at: datetime | None
    triaged_at: datetime | None = None
    closed_at: datetime | None
    bounty_awarded_at: datetime | None
    disclosed_at: datetime | None = None
    last_program_activity_at: datetime | None = None
    awarded: list[Money] = []
    awards: list[AwardRead] = []
