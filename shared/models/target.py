import uuid
from datetime import datetime
from functools import partial
from typing import TYPE_CHECKING

from pydantic import BaseModel, field_validator
from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint

from shared.definitions.constants import MAX_TARGET_BULK, MAX_TARGETS_IMPORT
from shared.definitions.infostealer import MAX_ERROR_LENGTH
from shared.definitions.rescan import MAX_RUN_ASSETS
from shared.enums.target import TargetType
from shared.enums.task_status import TaskStatus
from shared.models.bgp_summary import BgpSummaryRead, TargetBgpSummary
from shared.models.dns import DnsLookup, DnsLookupSummary
from shared.models.organization import (
    MAX_ORG_LEN,
    Organization,
    OrganizationSummary,
)
from shared.models.tag import MAX_TAG_LEN, TagSummary, TargetTag
from shared.models.whois import WhoisRecord, WhoisRecordSummary
from shared.utils.datetime import utc_now
from shared.utils.validation import clean_name

if TYPE_CHECKING:
    from shared.models.tag import Tag


MAX_TARGET_VALUE_LEN = 500
MAX_DISPLAY_NAME_LEN = 200


def _clean_labels(values: list[str] | None, max_len: int) -> list[str] | None:
    """Drop blank entries and cap each label's length."""
    if values is None:
        return None
    return [clean_name(v, max_len=max_len) for v in values if (v or "").strip()]


_clean_tags = partial(_clean_labels, max_len=MAX_TAG_LEN)
_clean_orgs = partial(_clean_labels, max_len=MAX_ORG_LEN)


class TargetValidationRequest(BaseModel):
    target_value: str


class TargetValidationBatch(BaseModel):
    values: list[str] = Field(..., min_length=1, max_length=MAX_TARGETS_IMPORT)
    project_slug: str | None = Field(
        default=None, description="Project whose existing targets are matched."
    )


class TargetValidationResponse(BaseModel):
    valid: bool
    target_type: TargetType | None
    error: str | None
    target_value: str
    target_id: uuid.UUID | None = Field(
        default=None, description="The project's target with this value."
    )


class TargetOrganization(SQLModel, table=True):
    __tablename__ = "target_organizations"

    target_id: uuid.UUID = Field(
        foreign_key="targets.id", primary_key=True, ondelete="CASCADE"
    )
    organization_id: uuid.UUID = Field(
        foreign_key="organizations.id", primary_key=True, ondelete="CASCADE"
    )


class TargetBase(SQLModel):
    target_value: str = Field(max_length=MAX_TARGET_VALUE_LEN)
    display_name: str | None = Field(default=None, max_length=MAX_DISPLAY_NAME_LEN)


class Target(TargetBase, table=True):
    __tablename__ = "targets"
    __table_args__ = (
        UniqueConstraint("target_value", "project_id", name="uq_target_value_project"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    target_type: TargetType
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    created_by: uuid.UUID = Field(foreign_key="users.id")

    whois_status: TaskStatus = Field(default=TaskStatus.PENDING, index=True)
    whois_error: str | None = Field(default=None, max_length=1000)
    whois_record: WhoisRecord | None = Relationship(
        sa_relationship_kwargs={"lazy": "selectin"},
    )
    whois_record_id: uuid.UUID | None = Field(
        default=None, foreign_key="whois_records.id", index=True, ondelete="SET NULL"
    )

    bgp_status: TaskStatus = Field(default=TaskStatus.PENDING, index=True)
    bgp_summary: TargetBgpSummary | None = Relationship(
        sa_relationship_kwargs={"lazy": "selectin", "passive_deletes": True},
    )

    seed_scans: bool = Field(default=True)
    new_checks: bool = Field(default=False)
    new_checks_swept_at: datetime | None = Field(default=None)

    dns_status: TaskStatus = Field(default=TaskStatus.PENDING, index=True)
    dns_error: str | None = Field(default=None, max_length=1000)
    dns_lookup: DnsLookup | None = Relationship(
        sa_relationship_kwargs={
            "lazy": "selectin",
            "foreign_keys": "Target.dns_lookup_id",
        },
    )
    dns_lookup_id: uuid.UUID | None = Field(
        default=None, foreign_key="dns_lookups.id", index=True, ondelete="SET NULL"
    )

    infostealer_status: TaskStatus = Field(default=TaskStatus.PENDING, index=True)
    infostealer_error: str | None = Field(default=None, max_length=MAX_ERROR_LENGTH)

    organizations: list["Organization"] = Relationship(
        link_model=TargetOrganization,
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    tags: list["Tag"] = Relationship(
        back_populates="targets",
        link_model=TargetTag,
        sa_relationship_kwargs={"lazy": "selectin"},
    )


class TargetCreate(TargetBase):
    project_slug: str
    organization_names: list[str] = Field(default_factory=list)
    tag_names: list[str] = Field(default_factory=list)
    seeds: list[str] = Field(default_factory=list, max_length=MAX_RUN_ASSETS)

    _tags = field_validator("tag_names")(_clean_tags)
    _orgs = field_validator("organization_names")(_clean_orgs)


class TargetBulkCreate(BaseModel):
    project_slug: str
    targets: list[str] = Field(
        ...,
        min_length=1,
        max_length=MAX_TARGET_BULK,
        description=f"Target values to import. At most {MAX_TARGET_BULK}.",
    )
    organization_names: list[str] = Field(default_factory=list)
    tag_names: list[str] = Field(default_factory=list)
    seeds: list[str] = Field(default_factory=list, max_length=MAX_RUN_ASSETS)

    _tags = field_validator("tag_names")(_clean_tags)
    _orgs = field_validator("organization_names")(_clean_orgs)


class TargetImportResult(BaseModel):
    target_value: str
    success: bool
    target_type: TargetType | None = None
    target_id: uuid.UUID | None = None
    error: str | None = None
    duplicate: bool = False


class TargetBulkCreateResponse(BaseModel):
    total: int
    imported: int
    failed: int
    skipped_duplicates: int
    results: list[TargetImportResult]


class TargetUpdate(SQLModel):
    display_name: str | None = Field(default=None, max_length=MAX_DISPLAY_NAME_LEN)
    organization_names: list[str] | None = None
    tag_names: list[str] | None = None
    seed_scans: bool | None = None
    new_checks: bool | None = None

    _tags = field_validator("tag_names")(_clean_tags)
    _orgs = field_validator("organization_names")(_clean_orgs)


class TargetRead(TargetBase):
    id: uuid.UUID
    target_type: TargetType
    project_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    created_by: uuid.UUID
    whois_status: TaskStatus
    whois_error: str | None
    whois_record_id: uuid.UUID | None
    whois: WhoisRecordSummary | None = None
    bgp_status: TaskStatus
    bgp: BgpSummaryRead | None = None
    dns_status: TaskStatus = TaskStatus.PENDING
    dns_error: str | None = None
    dns_lookup_id: uuid.UUID | None = None
    dns: DnsLookupSummary | None = None
    infostealer_status: TaskStatus = TaskStatus.PENDING
    infostealer_error: str | None = None
    organizations: list[OrganizationSummary] = Field(default_factory=list)
    tags: list[TagSummary] = Field(default_factory=list)
    seed_scans: bool = True
    new_checks: bool = False
    seed_count: int | None = None


class TargetImportItem(BaseModel):
    target_value: str
    tags: list[str] = Field(default_factory=list)
    organizations: list[str] = Field(default_factory=list)
    display_name: str | None = None
    seeds: list[str] = Field(default_factory=list, max_length=MAX_RUN_ASSETS)

    _tags = field_validator("tags")(_clean_tags)
    _orgs = field_validator("organizations")(_clean_orgs)


class TargetImportRequest(BaseModel):
    project_slug: str
    targets: list[TargetImportItem] = Field(
        ...,
        min_length=1,
        max_length=MAX_TARGETS_IMPORT,
        description=f"Targets to import. At most {MAX_TARGETS_IMPORT}.",
    )
    organization_names: list[str] = Field(
        default_factory=list,
        description="Organizations added to every imported target.",
    )
    tag_names: list[str] = Field(
        default_factory=list,
        description="Tags added to every imported target.",
    )

    _tags = field_validator("tag_names")(_clean_tags)
    _orgs = field_validator("organization_names")(_clean_orgs)
