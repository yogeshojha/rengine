import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField
from sqlalchemy import BigInteger, Column, Text
from sqlmodel import Field, Index, SQLModel, UniqueConstraint

from shared.definitions.asset_query import MAX_QUERY_LENGTH
from shared.definitions.endpoints import MAX_HOST_LENGTH, MAX_URL_LENGTH
from shared.definitions.secrets import (
    MAX_SUBJECT_LENGTH,
    SecretSource,
    SecretState,
)
from shared.definitions.surface import MAX_SELECTED_ROWS
from shared.definitions.vulnerabilities import CoverageStatus
from shared.models._columns import json_dict, nullable_text
from shared.models.asset_query import MatchEvidence, QueryError
from shared.utils.datetime import utc_now


class Secret(SQLModel, table=True):
    """One value read out of a stored response."""

    __tablename__ = "secrets"
    __table_args__ = (
        UniqueConstraint("scan_id", "fingerprint", name="uq_secret_scan_fingerprint"),
        Index("ix_secrets_scan_discovered", "scan_id", "discovered_at"),
        Index("ix_secrets_target_discovered", "target_id", "discovered_at"),
        Index("ix_secrets_scan_state", "scan_id", "state"),
        Index("ix_secrets_scan_kind", "scan_id", "kind"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    scan_id: uuid.UUID = Field(foreign_key="scans.id", index=True, ondelete="CASCADE")
    target_id: uuid.UUID = Field(
        foreign_key="targets.id", index=True, ondelete="CASCADE"
    )
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)

    fingerprint: str = Field(max_length=64, index=True)
    kind: str = Field(max_length=40, index=True)
    group: str = Field(max_length=24, index=True)
    vendor: str = Field(default="", max_length=60)
    state: str = Field(default=SecretState.EXPOSED.value, max_length=16, index=True)
    is_secret: bool = Field(default=True)

    # the value
    value: str = Field(sa_column=Column(Text, nullable=False))
    subject: str | None = Field(default=None, max_length=MAX_SUBJECT_LENGTH, index=True)
    meta: dict = json_dict()

    # where it was read, first sighting
    host: str = Field(max_length=MAX_HOST_LENGTH, index=True)
    url: str = Field(max_length=MAX_URL_LENGTH)
    http_asset_id: uuid.UUID | None = Field(default=None, index=True)
    source: str = Field(default=SecretSource.BODY.value, max_length=16)
    context: str | None = nullable_text()

    sightings: int = Field(default=1)
    hosts: int = Field(default=1)

    discovered_at: datetime = Field(default_factory=utc_now, index=True)
    created_at: datetime = Field(default_factory=utc_now)


class SecretSighting(SQLModel, table=True):
    """One place a secret was read."""

    __tablename__ = "secret_sightings"
    __table_args__ = (
        UniqueConstraint("secret_id", "url", "source", name="uq_sighting_secret_url"),
        Index("ix_secret_sightings_scan_host", "scan_id", "host"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    secret_id: uuid.UUID = Field(
        foreign_key="secrets.id", index=True, ondelete="CASCADE"
    )
    scan_id: uuid.UUID = Field(foreign_key="scans.id", index=True, ondelete="CASCADE")
    target_id: uuid.UUID = Field(
        foreign_key="targets.id", index=True, ondelete="CASCADE"
    )
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)

    host: str = Field(max_length=MAX_HOST_LENGTH)
    url: str = Field(max_length=MAX_URL_LENGTH)
    http_asset_id: uuid.UUID | None = Field(default=None, index=True)
    source: str = Field(default=SecretSource.BODY.value, max_length=16)
    offset: int = Field(default=0)
    context: str | None = nullable_text()

    created_at: datetime = Field(default_factory=utc_now)


class SecretCoverage(SQLModel, table=True):
    """What the miner read for one scan, per source."""

    __tablename__ = "secret_coverage"
    __table_args__ = (
        UniqueConstraint("scan_id", "source", name="uq_secret_coverage_scan_source"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    scan_id: uuid.UUID = Field(foreign_key="scans.id", index=True, ondelete="CASCADE")
    target_id: uuid.UUID = Field(
        foreign_key="targets.id", index=True, ondelete="CASCADE"
    )
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)

    source: str = Field(max_length=24)
    status: str = Field(default=CoverageStatus.COMPLETED.value, max_length=16)

    documents_total: int = Field(default=0)
    documents_read: int = Field(default=0)
    bytes_read: int = Field(default=0, sa_column=Column(BigInteger, nullable=False))
    truncated: int = Field(default=0)
    skipped: int = Field(default=0)
    detectors: int = Field(default=0)
    matches: int = Field(default=0)
    secrets: int = Field(default=0)
    dropped: dict = json_dict()
    error: str | None = Field(default=None, max_length=2000)

    started_at: datetime = Field(default_factory=utc_now)
    ended_at: datetime | None = Field(default=None)
    duration_seconds: float | None = Field(default=None)


# ---------- read models ----------


class SecretRead(BaseModel):
    id: uuid.UUID
    scan_id: uuid.UUID
    target_id: uuid.UUID
    target_value: str | None = None
    fingerprint: str
    kind: str
    kind_label: str
    group: str
    group_label: str
    vendor: str = ""
    state: str
    state_label: str
    is_secret: bool = True
    value: str
    subject: str | None = None
    meta: dict = PydanticField(default_factory=dict)
    host: str
    url: str
    http_asset_id: uuid.UUID | None = None
    source: str
    source_label: str = ""
    sightings: int = 1
    hosts: int = 1
    discovered_at: datetime
    is_new: bool = False
    matched_in: list[MatchEvidence] = PydanticField(default_factory=list)


class SecretSightingRead(BaseModel):
    id: uuid.UUID
    host: str
    url: str
    http_asset_id: uuid.UUID | None = None
    source: str
    source_label: str = ""
    offset: int = 0
    context: str | None = None


class SecretDetail(SecretRead):
    context: str | None = None
    sightings_shown: list[SecretSightingRead] = PydanticField(default_factory=list)
    sightings_truncated: bool = False


class SecretCoverageRow(BaseModel):
    source: str
    source_label: str
    status: str
    documents_total: int = 0
    documents_read: int = 0
    bytes_read: int = 0
    truncated: int = 0
    skipped: int = 0
    detectors: int = 0
    matches: int = 0
    secrets: int = 0
    dropped: dict[str, int] = PydanticField(default_factory=dict)
    error: str | None = None


class SecretCoverageRead(BaseModel):
    ran: bool = False
    partial: bool = False
    scans: int = 0
    documents_total: int = 0
    documents_read: int = 0
    bytes_read: int = 0
    truncated: int = 0
    detectors: int = 0
    secrets: int = 0
    exposed: int = 0
    rows: list[SecretCoverageRow] = PydanticField(default_factory=list)


class SecretFacet(BaseModel):
    key: str
    label: str
    count: int = 0


class SecretFacets(BaseModel):
    state: list[SecretFacet] = PydanticField(default_factory=list)
    group: list[SecretFacet] = PydanticField(default_factory=list)
    kind: list[SecretFacet] = PydanticField(default_factory=list)
    vendor: list[SecretFacet] = PydanticField(default_factory=list)
    source: list[SecretFacet] = PydanticField(default_factory=list)
    subject: list[SecretFacet] = PydanticField(default_factory=list)


class SecretPage(BaseModel):
    items: list[SecretRead] = PydanticField(default_factory=list)
    total: int = 0
    total_capped: bool = False
    error: QueryError | None = None


class SecretFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")
    q: str | None = PydanticField(default=None, max_length=MAX_QUERY_LENGTH)
    ids: list[uuid.UUID] = PydanticField(
        default_factory=list, max_length=MAX_SELECTED_ROWS
    )
    limit: int = PydanticField(default=50, ge=1, le=500)
    offset: int = PydanticField(default=0, ge=0)
    sort: str | None = None
    direction: str | None = None
