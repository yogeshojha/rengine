import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator
from sqlmodel import Field, SQLModel, UniqueConstraint

from shared.utils.datetime import utc_now

MAX_SCAN_TAG_LEN = 50
MAX_TAGS_PER_CHANGE = 20
MAX_TAGGED_SCANS = 500


def fold_scan_tag(value: str) -> str:
    return " ".join(value.split()).lower()


def scan_tag_name(value: str) -> str:
    name = fold_scan_tag(value)
    if not name:
        msg = "Tag name is empty."
        raise ValueError(msg)
    if len(name) > MAX_SCAN_TAG_LEN:
        msg = f"Tag name is longer than {MAX_SCAN_TAG_LEN} characters."
        raise ValueError(msg)
    return name


def scan_tag_names(values: list[str]) -> list[str]:
    return list(dict.fromkeys(scan_tag_name(v) for v in values))


class ScanTag(SQLModel, table=True):
    __tablename__ = "scan_tags"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_scan_tags_project_name"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(
        foreign_key="projects.id", index=True, ondelete="CASCADE"
    )
    name: str = Field(max_length=MAX_SCAN_TAG_LEN)
    created_at: datetime = Field(default_factory=utc_now)
    created_by: uuid.UUID | None = Field(
        default=None, foreign_key="users.id", ondelete="SET NULL"
    )


class ScanTagLink(SQLModel, table=True):
    __tablename__ = "scan_tag_links"

    scan_id: uuid.UUID = Field(
        foreign_key="scans.id", primary_key=True, ondelete="CASCADE"
    )
    tag_id: uuid.UUID = Field(
        foreign_key="scan_tags.id", primary_key=True, index=True, ondelete="CASCADE"
    )


class ScanTagSummary(BaseModel):
    id: uuid.UUID
    name: str


class ScanTagRead(ScanTagSummary):
    scan_count: int = 0


class ScanTagChange(BaseModel):
    scan_ids: list[uuid.UUID] = Field(min_length=1, max_length=MAX_TAGGED_SCANS)
    add: list[str] = Field(default_factory=list, max_length=MAX_TAGS_PER_CHANGE)
    remove: list[str] = Field(default_factory=list, max_length=MAX_TAGS_PER_CHANGE)

    @field_validator("add", "remove")
    @classmethod
    def _names(cls, v: list[str]) -> list[str]:
        return scan_tag_names(v)


class ScanTagAssignment(BaseModel):
    scan_id: uuid.UUID
    tags: list[ScanTagSummary]
