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


class LoginResponse(BaseModel):
    mfa_required: bool = False
    mfa_token: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"  # noqa: S105


class TwoFactorLoginRequest(BaseModel):
    mfa_token: str
    code: str


class PasswordChangeRequest(BaseModel):
    user_id: UUID | None = None
    current_password: str | None = None
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, password: str) -> str:
        return validate_password_strength(password)


class UsernameChangeRequest(BaseModel):
    user_id: UUID | None = None
    new_username: str = Field(max_length=50)

    @field_validator("new_username")
    @classmethod
    def validate_username_field(cls, username: str) -> str:
        return validate_username(username)
