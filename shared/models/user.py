import uuid
import uuid as uuid_pkg
from datetime import datetime

from sqlmodel import Field, SQLModel

from shared.utils.datetime import utc_now

# Password policy
MIN_PASSWORD_SCORE = 3
MIN_PASSWORD_LENGTH = 10


class UserBase(SQLModel):
    email: str = Field(unique=True, index=True, max_length=255)
    username: str = Field(unique=True, index=True, max_length=50)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)


class User(UserBase, table=True):
    """User database model."""

    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime | None = Field(default=None)


class UserCreate(SQLModel):
    email: str
    username: str
    password: str


class UserRead(UserBase):
    id: uuid_pkg.UUID
    created_at: datetime
    updated_at: datetime | None = None
