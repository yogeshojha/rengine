import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlmodel import Field, SQLModel, UniqueConstraint

from shared.utils.datetime import utc_now

MAX_ORG_LEN = 100
MAX_ORG_DESCRIPTION_LEN = 500


class OrganizationSummary(BaseModel):
    id: uuid.UUID
    name: str
    slug: str


class OrganizationBase(SQLModel):
    name: str = Field(max_length=MAX_ORG_LEN)
    description: str | None = Field(default=None, max_length=MAX_ORG_DESCRIPTION_LEN)


class Organization(OrganizationBase, table=True):
    __tablename__ = "organizations"
    __table_args__ = (
        UniqueConstraint("name", "project_id", name="uq_organization_name_project"),
        UniqueConstraint("slug", "project_id", name="uq_organization_slug_project"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    slug: str = Field(max_length=150, index=True)
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)
    created_at: datetime = Field(default_factory=utc_now)
    created_by: uuid.UUID = Field(foreign_key="users.id")


class OrganizationCreate(OrganizationBase):
    project_slug: str


class OrganizationUpdate(SQLModel):
    name: str | None = Field(default=None, max_length=MAX_ORG_LEN)
    description: str | None = Field(default=None, max_length=MAX_ORG_DESCRIPTION_LEN)


class OrganizationRead(OrganizationBase):
    id: uuid.UUID
    slug: str
    project_id: uuid.UUID
    created_at: datetime
    created_by: uuid.UUID
    target_count: int = 0
