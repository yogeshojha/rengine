import uuid
from datetime import datetime

from pydantic import BaseModel
from pydantic import Field as PydanticField
from sqlmodel import Field, SQLModel

from shared.definitions.wordlists import (
    MAX_SLUG_LENGTH,
    MAX_WORDLIST_UPLOAD,
    WordlistKind,
    WordlistOrigin,
)
from shared.utils.datetime import utc_now


class Wordlist(SQLModel, table=True):
    """One list a guessing stage can read. Shipped lists and uploads share the row shape."""

    __tablename__ = "wordlists"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    slug: str = Field(max_length=MAX_SLUG_LENGTH, unique=True, index=True)
    name: str = Field(max_length=200)
    description: str = Field(default="", max_length=1000)
    origin: str = Field(default=WordlistOrigin.CUSTOM.value, max_length=16, index=True)
    kind: str = Field(default=WordlistKind.SUBDOMAIN.value, max_length=16, index=True)
    # relative to the root its origin names, never an absolute path
    filename: str = Field(max_length=200)
    words: int = Field(default=0)
    bytes: int = Field(default=0)
    uploaded_by: uuid.UUID | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class WordlistRead(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    description: str
    origin: str
    kind: str
    words: int
    bytes: int
    created_at: datetime
    updated_at: datetime


class WordlistUpdate(BaseModel):
    name: str | None = PydanticField(default=None, max_length=200)
    description: str | None = PydanticField(default=None, max_length=1000)


class WordlistFile(BaseModel):
    filename: str = PydanticField(max_length=200)
    content: str
    name: str | None = PydanticField(default=None, max_length=200)
    description: str | None = PydanticField(default=None, max_length=1000)


class WordlistUploadRequest(BaseModel):
    kind: str = WordlistKind.SUBDOMAIN.value
    files: list[WordlistFile] = PydanticField(
        default_factory=list, max_length=MAX_WORDLIST_UPLOAD
    )


class WordlistRejection(BaseModel):
    filename: str
    reason: str


class WordlistUploadResult(BaseModel):
    stored: list[WordlistRead] = PydanticField(default_factory=list)
    rejected: list[WordlistRejection] = PydanticField(default_factory=list)
