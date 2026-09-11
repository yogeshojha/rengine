import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator
from sqlmodel import Field, SQLModel

from shared.definitions.notes import (
    MAX_ASSET_KEY,
    MAX_ASSET_LABEL,
    MAX_NOTE_BODY,
    MAX_NOTE_TAGS,
    MAX_NOTE_TITLE,
    NoteStatus,
)
from shared.definitions.surface import SURFACE_ORDER
from shared.models.tag import TagSummary
from shared.utils.datetime import utc_now


class NoteTag(SQLModel, table=True):
    __tablename__ = "note_tags"

    note_id: uuid.UUID = Field(
        foreign_key="notes.id", primary_key=True, ondelete="CASCADE"
    )
    tag_id: uuid.UUID = Field(
        foreign_key="tags.id", primary_key=True, ondelete="CASCADE"
    )


class Note(SQLModel, table=True):
    __tablename__ = "notes"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(
        foreign_key="projects.id", index=True, ondelete="CASCADE"
    )
    target_id: uuid.UUID = Field(
        foreign_key="targets.id", index=True, ondelete="CASCADE"
    )
    scan_id: uuid.UUID | None = Field(
        default=None, foreign_key="scans.id", index=True, ondelete="SET NULL"
    )
    dimension: str | None = Field(default=None, max_length=32, index=True)
    asset_key: str | None = Field(default=None, max_length=MAX_ASSET_KEY, index=True)
    asset_label: str | None = Field(default=None, max_length=MAX_ASSET_LABEL)
    title: str | None = Field(default=None, max_length=MAX_NOTE_TITLE)
    body: str = Field(max_length=MAX_NOTE_BODY)
    status: str = Field(default=NoteStatus.OPEN.value, max_length=16, index=True)
    created_by: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now, index=True)
    updated_at: datetime = Field(default_factory=utc_now)


def _clean_anchor(
    dimension: str | None, asset_key: str | None
) -> tuple[str | None, str | None]:
    dimension = (dimension or "").strip() or None
    asset_key = (asset_key or "").strip() or None
    if dimension is not None and dimension not in SURFACE_ORDER:
        msg = f"Unknown dimension '{dimension}'."
        raise ValueError(msg)
    if (dimension is None) != (asset_key is None):
        msg = "An asset note needs both a dimension and an asset."
        raise ValueError(msg)
    return dimension, asset_key


class NoteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: uuid.UUID
    scan_id: uuid.UUID | None = None
    dimension: str | None = Field(default=None, max_length=32)
    asset_key: str | None = Field(default=None, max_length=MAX_ASSET_KEY)
    asset_label: str | None = Field(default=None, max_length=MAX_ASSET_LABEL)
    title: str | None = Field(default=None, max_length=MAX_NOTE_TITLE)
    body: str = Field(min_length=1, max_length=MAX_NOTE_BODY)
    status: str = Field(default=NoteStatus.OPEN.value, max_length=16)
    tag_ids: list[uuid.UUID] = Field(min_length=1, max_length=MAX_NOTE_TAGS)

    @model_validator(mode="after")
    def _anchored_and_tagged(self):
        self.dimension, self.asset_key = _clean_anchor(self.dimension, self.asset_key)
        if not self.body.strip():
            msg = "Write something in the note."
            raise ValueError(msg)
        self.body = self.body.strip()
        self.tag_ids = list(dict.fromkeys(self.tag_ids))
        return self


class NoteUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=MAX_NOTE_TITLE)
    body: str | None = Field(default=None, max_length=MAX_NOTE_BODY)
    status: str | None = Field(default=None, max_length=16)
    tag_ids: list[uuid.UUID] | None = Field(default=None, max_length=MAX_NOTE_TAGS)

    @model_validator(mode="after")
    def _keeps_a_tag(self):
        if self.tag_ids is not None:
            self.tag_ids = list(dict.fromkeys(self.tag_ids))
            if not self.tag_ids:
                msg = "A note needs at least one tag."
                raise ValueError(msg)
        if self.body is not None:
            self.body = self.body.strip()
            if not self.body:
                msg = "Write something in the note."
                raise ValueError(msg)
        return self


class NoteRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    target_id: uuid.UUID
    target_value: str
    scan_id: uuid.UUID | None = None
    dimension: str | None = None
    asset_key: str | None = None
    asset_label: str | None = None
    title: str | None = None
    body: str
    status: str
    tags: list[TagSummary] = Field(default_factory=list)
    created_by: uuid.UUID
    author: str | None = None
    created_at: datetime
    updated_at: datetime


class NoteCount(BaseModel):
    """Note totals for one asset, scan or target."""

    key: str
    total: int = 0
    open: int = 0
