import uuid
from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy import Column, UniqueConstraint
from sqlalchemy.types import JSON
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel

from shared.definitions.lookalikes import (
    MAX_DOMAIN_LENGTH,
    MAX_REGISTRAR_LENGTH,
    MAX_TITLE_LENGTH,
    MAX_URL_LENGTH,
    LookalikeState,
)
from shared.utils.datetime import utc_now


class LookalikeDomain(SQLModel, table=True):
    __tablename__ = "lookalike_domains"
    __table_args__ = (
        UniqueConstraint("scan_id", "domain", name="uq_lookalike_domains_scan_domain"),
    )

    id: uuid.UUID = SQLField(default_factory=uuid.uuid4, primary_key=True)
    scan_id: uuid.UUID = SQLField(
        foreign_key="scans.id", index=True, ondelete="CASCADE"
    )
    target_id: uuid.UUID = SQLField(
        foreign_key="targets.id", index=True, ondelete="CASCADE"
    )
    project_id: uuid.UUID = SQLField(foreign_key="projects.id", index=True)

    apex: str = SQLField(max_length=MAX_DOMAIN_LENGTH)
    domain: str = SQLField(max_length=MAX_DOMAIN_LENGTH, index=True)
    display: str = SQLField(max_length=MAX_DOMAIN_LENGTH)
    technique: str = SQLField(max_length=32)
    verdict: str = SQLField(max_length=16, index=True)
    link_reason: str | None = SQLField(default=None, max_length=16)

    a: list = SQLField(default_factory=list, sa_column=Column(JSON, nullable=False))
    aaaa: list = SQLField(default_factory=list, sa_column=Column(JSON, nullable=False))
    mx: list = SQLField(default_factory=list, sa_column=Column(JSON, nullable=False))
    ns: list = SQLField(default_factory=list, sa_column=Column(JSON, nullable=False))
    parked: bool = SQLField(default=False)

    http_status: int | None = SQLField(default=None)
    final_url: str | None = SQLField(default=None, max_length=MAX_URL_LENGTH)
    title: str | None = SQLField(default=None, max_length=MAX_TITLE_LENGTH)
    similarity: int | None = SQLField(default=None)

    registered_at: datetime | None = SQLField(default=None)
    registrar: str | None = SQLField(default=None, max_length=MAX_REGISTRAR_LENGTH)

    first_seen: datetime = SQLField(default_factory=utc_now)
    discovered_at: datetime = SQLField(default_factory=utc_now)
    created_at: datetime = SQLField(default_factory=utc_now)


class LookalikeTriage(SQLModel, table=True):
    __tablename__ = "lookalike_triage"
    __table_args__ = (
        UniqueConstraint(
            "target_id", "domain", name="uq_lookalike_triage_target_domain"
        ),
    )

    id: uuid.UUID = SQLField(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = SQLField(foreign_key="projects.id", index=True)
    target_id: uuid.UUID = SQLField(
        foreign_key="targets.id", index=True, ondelete="CASCADE"
    )
    domain: str = SQLField(max_length=MAX_DOMAIN_LENGTH)
    state: str = SQLField(default=LookalikeState.OPEN.value, max_length=16)
    updated_at: datetime = SQLField(default_factory=utc_now)


class LookalikeRead(BaseModel):
    id: uuid.UUID
    scan_id: uuid.UUID
    target_id: uuid.UUID
    apex: str
    domain: str
    display: str
    technique: str
    verdict: str
    link_reason: str | None = None
    a: list[str] = Field(default_factory=list)
    aaaa: list[str] = Field(default_factory=list)
    mx: list[str] = Field(default_factory=list)
    ns: list[str] = Field(default_factory=list)
    parked: bool = False
    http_status: int | None = None
    final_url: str | None = None
    title: str | None = None
    similarity: int | None = None
    registered_at: datetime | None = None
    registrar: str | None = None
    first_seen: datetime
    discovered_at: datetime
    state: str = LookalikeState.OPEN.value


class LookalikeSummary(BaseModel):
    """Registered lookalikes of one scan, with counts per verdict."""

    covered: bool = False
    scan_id: uuid.UUID | None = None
    target_id: uuid.UUID | None = None
    observed_at: datetime | None = None
    apex: str | None = None
    permutations: int | None = None
    fetched: bool = False
    rows: list[LookalikeRead] = Field(default_factory=list)
    verdicts: dict[str, int] = Field(default_factory=dict)
    registered: int = 0


class LookalikeTriageUpdate(BaseModel):
    target_id: uuid.UUID
    domains: list[str] = Field(min_length=1, max_length=500)
    state: LookalikeState
