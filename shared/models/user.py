import uuid
import uuid as uuid_pkg
from datetime import datetime

from sqlalchemy import Column
from sqlalchemy.types import JSON
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
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    totp_secret_encrypted: str | None = Field(default=None)
    totp_enabled: bool = Field(default=False)
    totp_backup_codes: list | None = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime | None = Field(default=None)


class UserCreate(SQLModel):
    email: str
    username: str
    password: str


class UserRead(UserBase):
    id: uuid_pkg.UUID
    totp_enabled: bool = False
    created_at: datetime
    updated_at: datetime | None = None


class UserSummary(SQLModel):
    id: uuid_pkg.UUID
    username: str
