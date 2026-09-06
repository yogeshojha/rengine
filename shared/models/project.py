import uuid
from datetime import datetime
from functools import partial

from pydantic import BaseModel, field_validator
from sqlmodel import Field, SQLModel

from shared.utils.datetime import utc_now
from shared.utils.validation import clean_name


class ProjectBase(SQLModel):
    name: str = Field(max_length=50)

    _validate_name = field_validator("name")(partial(clean_name, max_len=50))


class Project(ProjectBase, table=True):
    __tablename__ = "projects"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    slug: str = Field(max_length=100, unique=True, index=True)
    description: str | None = Field(default=None, max_length=1000)
    label: str | None = Field(default=None, max_length=50)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utc_now)
    created_by: uuid.UUID = Field(foreign_key="users.id")


class ProjectCreate(ProjectBase):
    description: str | None = None
    label: str | None = None


class ProjectRead(ProjectBase):
    id: uuid.UUID
    slug: str
    description: str | None = None
    label: str | None = None
    is_active: bool
    created_at: datetime
    created_by: uuid.UUID


class ProjectSummary(BaseModel):
    project: ProjectRead
    stats: dict[str, int]
