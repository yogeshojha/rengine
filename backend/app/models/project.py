import uuid
from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class ProjectBase(SQLModel):
    name: str = Field(max_length=50)


class Project(ProjectBase, table=True):
    __tablename__ = "projects"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    slug: str = Field(max_length=100, unique=True, index=True)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    created_by: uuid.UUID = Field(foreign_key="users.id")


class ProjectCreate(ProjectBase):
    pass


class ProjectRead(ProjectBase):
    id: uuid.UUID
    slug: str
    is_active: bool
    created_at: datetime
    created_by: uuid.UUID
