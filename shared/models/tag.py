import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, field_validator
from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint

from app.utils.validation import validate_hex_color
from shared.utils.datetime import utc_now

if TYPE_CHECKING:
    from shared.models.target import Target


class TagSummary(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    color: str


class TargetTag(SQLModel, table=True):
    __tablename__ = "target_tags"

    target_id: uuid.UUID = Field(foreign_key="targets.id", primary_key=True)
    tag_id: uuid.UUID = Field(foreign_key="tags.id", primary_key=True)


class TagBase(SQLModel):
    name: str = Field(max_length=50)
    color: str = Field(
        max_length=7, description="Hex color code, e.g., #FF5733", default="#6B7280"
    )

    @field_validator("color")
    @classmethod
    def validate_color_format(cls, v: str) -> str:
        return validate_hex_color(v)


class Tag(TagBase, table=True):
    __tablename__ = "tags"
    __table_args__ = (
        UniqueConstraint("name", "project_id", name="uq_tag_name_project"),
        UniqueConstraint("slug", "project_id", name="uq_tag_slug_project"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    slug: str = Field(max_length=100, index=True)
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)
    created_at: datetime = Field(default_factory=lambda: utc_now)
    created_by: uuid.UUID = Field(foreign_key="users.id")

    targets: list["Target"] = Relationship(
        link_model=TargetTag, sa_relationship_kwargs={"lazy": "selectin"}
    )


class TagCreate(TagBase):
    project_slug: str


class TagUpdate(SQLModel):
    name: str | None = Field(default=None, max_length=50)
    color: str | None = Field(
        default=None, max_length=7, description="Hex color code, e.g., #FF5733"
    )

    @field_validator("color")
    @classmethod
    def validate_color_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return validate_hex_color(v)


class TagRead(TagBase):
    id: uuid.UUID
    slug: str
    project_id: uuid.UUID
    created_at: datetime
    created_by: uuid.UUID


# These tags will always exist in every project
PREDEFINED_TAGS = [
    {"name": "production", "color": "#DC2626"},
    {"name": "staging", "color": "#F59E0B"},
    {"name": "dev", "color": "#3B82F6"},
    {"name": "internal", "color": "#8B5CF6"},
    {"name": "external", "color": "#10B981"},
]
