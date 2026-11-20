import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from shared.utils.datetime import utc_now


class ProjectMember(SQLModel, table=True):
    """A standard user who opens one project."""

    __tablename__ = "project_members"

    project_id: uuid.UUID = Field(
        foreign_key="projects.id", primary_key=True, ondelete="CASCADE"
    )
    user_id: uuid.UUID = Field(
        foreign_key="users.id", primary_key=True, index=True, ondelete="CASCADE"
    )
    created_at: datetime = Field(default_factory=utc_now)
    added_by: uuid.UUID | None = Field(
        default=None, foreign_key="users.id", ondelete="SET NULL"
    )
