"""Investigations: one verdict per finding, and the plans that reached it."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PField
from sqlalchemy import Column, Index, Text, UniqueConstraint
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from shared.definitions.ai import MAX_MODEL_ID
from shared.definitions.investigate import (
    INVESTIGATE_DIMENSION,
    MAX_HOST,
    MAX_PLAN_REASON_CHARS,
    MAX_TEMPLATE_ID,
    PlanKind,
    PlanState,
    Verdict,
)
from shared.definitions.notes import MAX_ASSET_KEY
from shared.models.ask import TraceStep
from shared.utils.datetime import utc_now


class Investigation(SQLModel, table=True):
    __tablename__ = "investigations"
    __table_args__ = (
        UniqueConstraint("target_id", "fingerprint", name="uq_investigation_finding"),
        Index("ix_investigations_scan_verdict", "scan_id", "verdict"),
        Index("ix_investigations_project_updated", "project_id", "updated_at"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(
        foreign_key="projects.id", index=True, ondelete="CASCADE"
    )
    target_id: uuid.UUID = Field(
        foreign_key="targets.id", index=True, ondelete="CASCADE"
    )
    scan_id: uuid.UUID = Field(foreign_key="scans.id", index=True, ondelete="CASCADE")
    dimension: str = Field(default=INVESTIGATE_DIMENSION, max_length=32)
    fingerprint: str = Field(max_length=MAX_ASSET_KEY)

    verdict: str = Field(default=Verdict.PENDING.value, max_length=24)
    rationale: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    trace: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    flags: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))

    # null when the known-exploited replay rule started it
    started_by: uuid.UUID | None = Field(
        default=None, foreign_key="users.id", ondelete="SET NULL"
    )
    by_rule: bool = Field(default=False)

    requests_spent: int = Field(default=0)
    # set when a plan reproduced the finding or the evidence was conclusive
    verified_at: datetime | None = Field(default=None)

    model: str | None = Field(default=None, max_length=MAX_MODEL_ID)
    input_tokens: int = Field(default=0)
    output_tokens: int = Field(default=0)
    cost_usd: float | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class InvestigationPlan(SQLModel, table=True):
    __tablename__ = "investigation_plans"
    __table_args__ = (
        Index("ix_investigation_plans_inv_created", "investigation_id", "created_at"),
        Index("ix_investigation_plans_state", "state"),
        Index("ix_investigation_plans_launched", "launched_scan_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    investigation_id: uuid.UUID = Field(
        foreign_key="investigations.id", index=True, ondelete="CASCADE"
    )
    kind: str = Field(default=PlanKind.REPLAY.value, max_length=16)
    template_id: str = Field(max_length=MAX_TEMPLATE_ID)
    template_name: str | None = Field(default=None, max_length=200)
    host: str = Field(max_length=MAX_HOST)
    reason: str | None = Field(default=None, max_length=MAX_PLAN_REASON_CHARS)

    state: str = Field(default=PlanState.PROPOSED.value, max_length=16)
    refusal_reason: str | None = Field(default=None, max_length=24)
    request_count: int | None = Field(default=None)

    approved_by: uuid.UUID | None = Field(
        default=None, foreign_key="users.id", ondelete="SET NULL"
    )
    approved_at: datetime | None = Field(default=None)
    launched_scan_id: uuid.UUID | None = Field(
        default=None, foreign_key="scans.id", ondelete="SET NULL"
    )
    result: str | None = Field(default=None, max_length=24)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


# ---------- read and write schemas ----------


class PlanRead(BaseModel):
    id: uuid.UUID
    kind: str
    kind_label: str
    template_id: str
    template_name: str | None = None
    host: str
    reason: str | None = None
    state: str
    state_label: str
    refusal_reason: str | None = None
    refusal_label: str | None = None
    request_count: int | None = None
    approved_by: uuid.UUID | None = None
    approved_at: datetime | None = None
    launched_scan_id: uuid.UUID | None = None
    result: str | None = None
    result_label: str | None = None
    created_at: datetime


class InvestigationRead(BaseModel):
    id: uuid.UUID
    target_id: uuid.UUID
    scan_id: uuid.UUID
    dimension: str
    fingerprint: str
    verdict: str
    verdict_label: str
    verified: bool
    rationale: str | None = None
    trace: list[TraceStep] = []
    by_rule: bool = False
    started_by: uuid.UUID | None = None
    requests_spent: int = 0
    verified_at: datetime | None = None
    model: str | None = None
    cost_usd: float | None = None
    plans: list[PlanRead] = []
    created_at: datetime
    updated_at: datetime


class InvestigateBrief(BaseModel):
    """What the finding sheet shows before anyone runs the agent."""

    investigation: InvestigationRead | None = None
    available: bool
    off_reason: str | None = None
    model: str | None = None


class InvestigateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scan_id: uuid.UUID
    fingerprint: str = PField(min_length=1, max_length=MAX_ASSET_KEY)


class PlanDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_ids: list[uuid.UUID] = PField(min_length=1, max_length=64)
