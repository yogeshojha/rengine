import uuid
from datetime import UTC, datetime

from pydantic import BaseModel
from sqlmodel import Field, Relationship, SQLModel

from app.enums.target import TargetType
from app.models.organization import Organization


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
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    created_by: uuid.UUID = Field(foreign_key="users.id")

    organizations: list["Organization"] = Relationship(
        link_model=TargetOrganization,
        sa_relationship_kwargs={"lazy": "selectin"},
    )


class TargetCreate(TargetBase):
    project_slug: str
    organization_slugs: list[str] = Field(default_factory=list)


class TargetUpdate(SQLModel):
    display_name: str | None = Field(default=None, max_length=200)
    organization_slugs: list[str] | None = None


class TargetRead(TargetBase):
    id: uuid.UUID
    project_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    created_by: uuid.UUID
    organization_ids: list[uuid.UUID] = Field(default_factory=list)
    target_type: TargetType


# BASE Models only for request and response schemas


class TargetValidationRequest(BaseModel):
    target_value: str


class TargetValidationResponse(BaseModel):
    valid: bool
    target_type: TargetType | None
    error: str | None
