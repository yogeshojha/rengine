import uuid

from sqlmodel import Field, SQLModel


class ProjectBase(SQLModel):
    __tablename__ = "projects"


class Project(ProjectBase, table=True):
    __tablename__ = "projects"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
