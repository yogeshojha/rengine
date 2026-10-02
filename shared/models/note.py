import re
import unicodedata
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from sqlalchemy import Column, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from shared.definitions.ask import plain_answer
from shared.definitions.notes import (
    MAX_ASSET_KEY,
    MAX_ASSET_LABEL,
    MAX_NOTE_BODY,
    MAX_NOTE_TAG_CHARS,
    MAX_NOTE_TAGS,
    MAX_NOTE_TITLE,
    NOTE_TAG_PUNCTUATION,
    TRIAGE_REASON_STATES,
    NoteStatus,
)
from shared.definitions.surface import SURFACE_ORDER, SurfaceDimension
from shared.utils.datetime import utc_now

_SPACE = re.compile(r"\s+")


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
    dimension: str | None = Field(default=None, max_length=32)
    asset_key: str | None = Field(default=None, max_length=MAX_ASSET_KEY)
    asset_label: str | None = Field(default=None, max_length=MAX_ASSET_LABEL)
    title: str | None = Field(default=None, max_length=MAX_NOTE_TITLE)
    body: str = Field(max_length=MAX_NOTE_BODY)
    status: str = Field(default=NoteStatus.OPEN.value, max_length=16, index=True)
    tags: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    )
    triage_state: str | None = Field(default=None, max_length=20)
    created_by: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now, index=True)
    updated_at: datetime = Field(default_factory=utc_now)


def note_tag(value: str) -> str:
    """A tag as stored: trimmed, no leading #, lowercase, whitespace as hyphens."""
    return _SPACE.sub("-", value.strip().lstrip("#").strip().lower())


def _tag_char(ch: str) -> bool:
    return (
        ch.isalnum()
        or ch in NOTE_TAG_PUNCTUATION
        or unicodedata.category(ch).startswith("M")
    )


def clean_note_tags(values: list[str]) -> list[str]:
    """Stored tags in the order given, duplicates and blanks dropped."""
    tags = list(dict.fromkeys(tag for tag in map(note_tag, values) if tag))
    for tag in tags:
        if len(tag) > MAX_NOTE_TAG_CHARS:
            msg = f"Tags are at most {MAX_NOTE_TAG_CHARS} characters."
            raise ValueError(msg)
        if not all(map(_tag_char, tag)):
            msg = (
                f'Tag "{tag}" has a character outside letters, digits, dot, '
                "underscore, hyphen and colon."
            )
            raise ValueError(msg)
    if len(tags) > MAX_NOTE_TAGS:
        msg = f"A note takes at most {MAX_NOTE_TAGS} tags."
        raise ValueError(msg)
    return tags


def clean_reason(value: str | None) -> str | None:
    """A triage reason as stored, or None when it is blank."""
    return plain_answer(value or "").strip() or None


def _clean_triage(state: str | None, dimension: str | None) -> str | None:
    state = (state or "").strip() or None
    if state is None:
        return None
    if state not in TRIAGE_REASON_STATES:
        msg = f"Unknown triage state '{state}'."
        raise ValueError(msg)
    if dimension != SurfaceDimension.VULNERABILITIES.value:
        msg = "A triage state applies to a note on a finding."
        raise ValueError(msg)
    return state


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
    tags: list[str] = Field(default_factory=list)
    triage_state: str | None = Field(default=None, max_length=20)

    @field_validator("tags")
    @classmethod
    def _tags(cls, value: list[str]) -> list[str]:
        return clean_note_tags(value)

    @model_validator(mode="after")
    def _anchored(self):
        self.dimension, self.asset_key = _clean_anchor(self.dimension, self.asset_key)
        self.triage_state = _clean_triage(self.triage_state, self.dimension)
        self.body = plain_answer(self.body).strip()
        if not self.body:
            msg = "Note body is required."
            raise ValueError(msg)
        return self


class NoteUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=MAX_NOTE_TITLE)
    body: str | None = Field(default=None, max_length=MAX_NOTE_BODY)
    status: str | None = Field(default=None, max_length=16)
    tags: list[str] | None = None

    @field_validator("tags")
    @classmethod
    def _tags(cls, value: list[str] | None) -> list[str] | None:
        return None if value is None else clean_note_tags(value)

    @model_validator(mode="after")
    def _body(self):
        if self.body is not None:
            self.body = plain_answer(self.body).strip()
            if not self.body:
                msg = "Note body is required."
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
    tags: list[str] = Field(default_factory=list)
    triage_state: str | None = None
    created_by: uuid.UUID
    author: str | None = None
    created_at: datetime
    updated_at: datetime
    scan_at: datetime | None = None
    finding_id: uuid.UUID | None = None


class NoteTagCount(BaseModel):
    name: str
    count: int


class NoteFilter(BaseModel):
    """The notes a list or a facet count reads."""

    target_ids: list[uuid.UUID] = Field(default_factory=list)
    scan_id: uuid.UUID | None = None
    scans: list[uuid.UUID] = Field(default_factory=list)
    dimensions: list[str] = Field(default_factory=list)
    asset_key: str | None = None
    assets: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    statuses: list[str] = Field(default_factory=list)
    authors: list[uuid.UUID] = Field(default_factory=list)
    triage: list[str] = Field(default_factory=list)
    search: str | None = None


class NoteFacet(BaseModel):
    value: str
    label: str | None = None
    count: int


class NoteAssetFacet(NoteFacet):
    dimension: str


class NoteScanFacet(NoteFacet):
    target_value: str
    at: datetime


class NoteFacets(BaseModel):
    total: int = 0
    targets: list[NoteFacet] = Field(default_factory=list)
    dimensions: list[NoteFacet] = Field(default_factory=list)
    assets: list[NoteAssetFacet] = Field(default_factory=list)
    scans: list[NoteScanFacet] = Field(default_factory=list)
    tags: list[NoteFacet] = Field(default_factory=list)
    authors: list[NoteFacet] = Field(default_factory=list)
    statuses: list[NoteFacet] = Field(default_factory=list)
    triage: list[NoteFacet] = Field(default_factory=list)
