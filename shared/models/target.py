import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel
from sqlmodel import Field, Relationship, SQLModel

from shared.enums.target import TargetType
from shared.enums.whois import WhoisStatus
from shared.models.organization import Organization, OrganizationSummary
from shared.models.tag import TagSummary, TargetTag
from shared.models.whois import WhoisRecord, WhoisRecordSummary
from shared.utils.datetime import utc_now

if TYPE_CHECKING:
    from shared.models.tag import Tag


class TargetValidationRequest(BaseModel):
    target_value: str


class TargetValidationResponse(BaseModel):
    valid: bool
    target_type: TargetType | None
    error: str | None
    target_value: str


class TargetOrganization(SQLModel, table=True):
    __tablename__ = "target_organizations"

    target_id: uuid.UUID = Field(foreign_key="targets.id", primary_key=True)
    organization_id: uuid.UUID = Field(foreign_key="organizations.id", primary_key=True)


class TargetBase(SQLModel):
    target_value: str = Field(max_length=500)
    display_name: str | None = Field(default=None, max_length=200)


class Target(TargetBase, table=True):
    __tablename__ = "targets"
    __table_args__ = ({"sqlite_autoincrement": True},)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    target_type: TargetType
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    created_by: uuid.UUID = Field(foreign_key="users.id")

    whois_status: WhoisStatus = Field(default=WhoisStatus.PENDING, index=True)
    whois_error: str | None = Field(default=None, max_length=1000)
    whois_record: WhoisRecord | None = Relationship(
        sa_relationship_kwargs={"lazy": "selectin"},
    )
    whois_record_id: uuid.UUID | None = Field(
        default=None, foreign_key="whois_records.id", index=True
    )

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


# bulk targets create/request/response models
class TargetBulkCreate(BaseModel):
    project_slug: str
    targets: list[str] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="List of target values to import (max 1000)",
    )
    organization_names: list[str] = Field(default_factory=list)
    tag_names: list[str] = Field(default_factory=list)


class TargetImportResult(BaseModel):
    # single target import result
    target_value: str
    success: bool
    target_type: TargetType | None = None
    target_id: uuid.UUID | None = None
    error: str | None = None


class TargetBulkCreateResponse(BaseModel):
    total: int
    imported: int
    failed: int
    skipped_duplicates: int
    results: list[TargetImportResult]


class TargetUpdate(SQLModel):
    display_name: str | None = Field(default=None, max_length=200)
    organization_names: list[str] | None = None
    tag_names: list[str] | None = None


class TargetRead(TargetBase):
    id: uuid.UUID
    target_type: TargetType
    project_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    created_by: uuid.UUID
    whois_status: WhoisStatus
    whois_error: str | None
    whois_record_id: uuid.UUID | None
    whois: WhoisRecordSummary | None = None
    organizations: list[OrganizationSummary] = Field(default_factory=list)
    tags: list[TagSummary] = Field(default_factory=list)


# imports for both json and csv support
class TargetImportItem(BaseModel):
    target_value: str
    tags: list[str] = Field(default_factory=list)
    organizations: list[str] = Field(default_factory=list)
    display_name: str | None = None


class TargetImportRequest(BaseModel):
    project_slug: str
    targets: list[TargetImportItem] = Field(
        ...,
        min_length=1,
        max_length=500,
        description="List of targets to import (max 500)",
    )
