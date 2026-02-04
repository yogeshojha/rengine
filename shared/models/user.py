import uuid
import uuid as uuid_pkg
from datetime import UTC, datetime

from pydantic import ValidationInfo, field_validator
from sqlmodel import Field, SQLModel

from app.utils.validation import validate_password_strength, validate_username

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
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    updated_at: datetime | None = Field(default=None)


class UserCreate(SQLModel):
    email: str
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def validate_username_field(cls, username: str) -> str:
        return validate_username(username)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, password: str, info: ValidationInfo) -> str:
        user_inputs = [info.data.get("email", ""), info.data.get("username", "")]
        return validate_password_strength(password, user_inputs=user_inputs)


class UserRead(UserBase):
    id: uuid_pkg.UUID
    created_at: datetime
    updated_at: datetime | None = None
