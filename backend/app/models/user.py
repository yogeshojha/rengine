import uuid
import uuid as uuid_pkg
from datetime import UTC, datetime

from pydantic import ValidationInfo, field_validator
from sqlmodel import Field, SQLModel
from zxcvbn import zxcvbn

from app.config import settings

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

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, password: str, info: ValidationInfo) -> str:
        # intentionally skipping password strength validation in DEBUG mode
        if settings.DEBUG:
            return password

        if len(password) < MIN_PASSWORD_LENGTH:
            return_error = (
                f"Password must be at least {MIN_PASSWORD_LENGTH} characters long"
            )
            raise ValueError(return_error)

        result = zxcvbn(
            password,
            user_inputs=[info.data.get("email", ""), info.data.get("username", "")],
        )

        if result["score"] < MIN_PASSWORD_SCORE:
            return_error = (
                "Password is too weak. Consider using a stronger password with a "
                "mix of uppercase, lowercase, numbers, and special characters."
            )
            raise ValueError(return_error)

        if result["guesses_log10"] < MIN_PASSWORD_SCORE:
            return_error = "Password is too guessable. Choose a less common password."
            raise ValueError(return_error)

        return password


class UserRead(UserBase):
    id: uuid_pkg.UUID
    created_at: datetime
    updated_at: datetime | None = None
