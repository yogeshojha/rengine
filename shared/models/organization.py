import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlmodel import Field, SQLModel, UniqueConstraint

from shared.utils.datetime import utc_now


class OrganizationSummary(BaseModel):
    id: uuid.UUID
    name: str
    slug: str


class OrganizationBase(SQLModel):
    name: str = Field(max_length=100)
    description: str | None = Field(default=None, max_length=500)


class Organization(OrganizationBase, table=True):
    __tablename__ = "organizations"
    __table_args__ = (
        UniqueConstraint("name", "project_id", name="uq_organization_name_project"),
        UniqueConstraint("slug", "project_id", name="uq_organization_slug_project"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    slug: str = Field(max_length=150, index=True)
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)
    created_at: datetime = Field(default_factory=utc_now)
    created_by: uuid.UUID = Field(foreign_key="users.id")


class OrganizationCreate(OrganizationBase):
    project_slug: str


class OrganizationUpdate(SQLModel):
    name: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class OrganizationRead(OrganizationBase):
    id: uuid.UUID
    slug: str
    project_id: uuid.UUID
    created_at: datetime
    created_by: uuid.UUID
