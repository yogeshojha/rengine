import uuid
from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy import UniqueConstraint
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel

from shared.definitions.estate import MAX_ESTATE_DOMAIN_LENGTH, EstateTriageState
from shared.utils.datetime import utc_now


class EstateTriage(SQLModel, table=True):
    __tablename__ = "estate_triage"
    __table_args__ = (
        UniqueConstraint(
            "project_id", "domain", name="uq_estate_triage_project_domain"
        ),
    )

    id: uuid.UUID = SQLField(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = SQLField(foreign_key="projects.id", index=True)
    domain: str = SQLField(max_length=MAX_ESTATE_DOMAIN_LENGTH)
    state: str = SQLField(default=EstateTriageState.OPEN.value, max_length=16)
    updated_at: datetime = SQLField(default_factory=utc_now)


class EstateSignal(BaseModel):
    kind: str
    label: str
    strength: str
    detail: str = ""
    hosts: list[str] = Field(default_factory=list)
    count: int = 0


class EstateSource(BaseModel):
    target_id: uuid.UUID
    target_value: str
    scan_id: uuid.UUID | None = None


class EstateDomain(BaseModel):
    domain: str
    target_id: uuid.UUID | None = None
    strength: int = 0
    state: str = EstateTriageState.OPEN.value
    signals: list[EstateSignal] = Field(default_factory=list)
    sources: list[EstateSource] = Field(default_factory=list)


class EstateProvider(BaseModel):
    name: str
    kind: str
    count: int = 0
    detail: str = ""
    query: str | None = None


class EstateNeighbourCert(BaseModel):
    host: str
    subject: str
    names: int = 0
    provider: str | None = None


class EstateCounts(BaseModel):
    untracked: int = 0
    tracked: int = 0
    providers: int = 0
    neighbour_names: int = 0
    by_reason: dict[str, int] = Field(default_factory=dict)


class TargetEstate(BaseModel):
    target_id: uuid.UUID
    scan_id: uuid.UUID | None = None
    root: str = ""
    counts: EstateCounts = Field(default_factory=EstateCounts)
    domains: list[EstateDomain] = Field(default_factory=list)
    providers: list[EstateProvider] = Field(default_factory=list)
    neighbours: list[EstateNeighbourCert] = Field(default_factory=list)
    own: list[str] = Field(default_factory=list)
    considered_targets: int = 0


class ProjectEstate(BaseModel):
    targets_examined: int = 0
    untracked: int = 0
    domains: list[EstateDomain] = Field(default_factory=list)


class EstateTriageUpdate(BaseModel):
    domains: list[str] = Field(min_length=1, max_length=500)
    state: EstateTriageState
