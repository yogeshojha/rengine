from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.utils.validation import validate_password_strength, validate_username


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105


class PasswordChangeRequest(BaseModel):
    # If None, change password for the current user; super user can change password for any user
    user_id: UUID | None = None
    current_password: str | None = None  # required for non super user
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, password: str) -> str:
        return validate_password_strength(password)


class UsernameChangeRequest(BaseModel):
    # If None, change own username; superuser can specify user_id
    user_id: UUID | None = None
    new_username: str = Field(max_length=50)

    @field_validator("new_username")
    @classmethod
    def validate_username_field(cls, username: str) -> str:
        return validate_username(username)
