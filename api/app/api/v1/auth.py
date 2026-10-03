from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import (
    BEARER_HEADERS,
    CurrentUser,
    security,
    user_for_payload,
)
from app.config import settings
from app.core.client_ip import client_id
from app.core.database import get_session
from app.core.ratelimit import (
    clear_failures,
    clear_token_grace,
    grant_token_grace,
    is_token_in_grace,
    is_token_revoked,
    record_failure,
    revoke_token,
    revoke_user_tokens,
    too_many_attempts,
)
from app.core.security import (
    ACCESS_TOKEN_COOKIE,
    AUTH_COOKIES,
    REFRESH_TOKEN_COOKIE,
    TOKEN_TYPE_MFA,
    TOKEN_TYPE_REFRESH,
    create_access_token,
    create_refresh_token,
    create_token,
    decode_token,
    hash_password_async,
    verify_password_async,
)
from app.utils.validation import (
    MAX_PASSWORD_LENGTH,
    MAX_USERNAME_LENGTH,
    validate_password_strength,
    validate_username,
)
from shared.logging import get_logger
from shared.models.user import User, UserRead
from shared.utils.datetime import utc_now

logger = get_logger(__name__)

_DUMMY_HASH = "$argon2id$v=19$m=65536,t=2,p=4$BFG/6RwwvAFTuluSmeDY5Q$ssCZOxGGhBFAM+3ub/t5TVPTUAyiL4Maz42kFYbcWts"

router = APIRouter(prefix="/auth", tags=["authentication"])

REFRESH_GRACE_SECONDS = 30
LOGIN_FAILURE_LIMIT = 10
LOGIN_ADDRESS_LIMIT = 50
LOGIN_WINDOW_SECONDS = 900
REAUTH_FAILURE_LIMIT = 5
REAUTH_WINDOW_SECONDS = 900


class LoginRequest(BaseModel):
    username: str = Field(max_length=MAX_USERNAME_LENGTH)
    password: str = Field(max_length=MAX_PASSWORD_LENGTH)


class LoginResponse(BaseModel):
    mfa_required: bool = False
    mfa_token: str | None = None


class PasswordChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str | None = Field(default=None, max_length=MAX_PASSWORD_LENGTH)
    new_password: str = Field(max_length=MAX_PASSWORD_LENGTH)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, password: str) -> str:
        return validate_password_strength(password)


class UsernameChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_username: str = Field(max_length=MAX_USERNAME_LENGTH)
    current_password: str = Field(max_length=MAX_PASSWORD_LENGTH)

    @field_validator("new_username")
    @classmethod
    def validate_username_field(cls, username: str) -> str:
        return validate_username(username)


def reauth_key(user: User) -> str:
    return f"auth:reauth:{user.id}"


async def require_current_password(user: User, password: str | None) -> None:
    """Refuse unless the password is the account's own."""
    if not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is required",
        )
    key = reauth_key(user)
    await too_many_attempts(key, limit=REAUTH_FAILURE_LIMIT, fail_closed=True)
    if not await verify_password_async(password, user.hashed_password):
        await record_failure(key, window_seconds=REAUTH_WINDOW_SECONDS)
        logger.warning("password confirmation failed", user=str(user.id))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )
    await clear_failures(key)


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
) -> None:
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=access_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )

    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/",
    )


async def reissue_session(response: Response, user: User) -> None:
    """Revoke every token the user holds and sign this client in again."""
    await revoke_user_tokens(user.id)
    set_auth_cookies(
        response,
        create_access_token(str(user.id)),
        create_refresh_token(str(user.id)),
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(
        key=ACCESS_TOKEN_COOKIE,
        path="/",
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
    )
    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE,
        path="/",
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    address = client_id(request)
    account_key = f"auth:login:{login_data.username.lower()}:{address}"
    address_key = f"auth:login-from:{address}"
    await too_many_attempts(account_key, limit=LOGIN_FAILURE_LIMIT, fail_closed=True)
    await too_many_attempts(address_key, limit=LOGIN_ADDRESS_LIMIT, fail_closed=True)

    user = await session.scalar(
        select(User).where(User.username == login_data.username)
    )
    valid = await verify_password_async(
        login_data.password, user.hashed_password if user else _DUMMY_HASH
    )

    if not user or not valid:
        await record_failure(account_key, window_seconds=LOGIN_WINDOW_SECONDS)
        await record_failure(address_key, window_seconds=LOGIN_WINDOW_SECONDS)
        logger.warning("login failed", username=login_data.username, address=address)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers=BEARER_HEADERS,
        )

    if not user.is_active:
        logger.warning("login refused for inactive account", user=str(user.id))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    await clear_failures(account_key)

    if user.totp_enabled:
        mfa_token = create_token(str(user.id), TOKEN_TYPE_MFA, timedelta(minutes=5))
        logger.info("password accepted, second factor required", user=str(user.id))
        return LoginResponse(mfa_required=True, mfa_token=mfa_token)

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    set_auth_cookies(response, access_token, refresh_token)
    logger.info("login succeeded", user=str(user.id), address=address)

    return LoginResponse()


@router.post("/refresh", status_code=status.HTTP_204_NO_CONTENT)
async def refresh_access_token(
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found",
            headers=BEARER_HEADERS,
        )

    payload = decode_token(refresh_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers=BEARER_HEADERS,
        )

    if payload.get("type") != TOKEN_TYPE_REFRESH:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers=BEARER_HEADERS,
        )

    jti = payload["jti"]
    user = await user_for_payload(payload, session)
    if await is_token_revoked(jti) and not await is_token_in_grace(jti):
        await revoke_user_tokens(user.id)
        logger.warning("revoked refresh token presented", user=str(user.id))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
            headers=BEARER_HEADERS,
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    new_access_token = create_access_token(str(user.id))
    new_refresh_token = create_refresh_token(str(user.id))

    await grant_token_grace(jti, REFRESH_GRACE_SECONDS)
    await revoke_token(jti, int(payload["exp"] - utc_now().timestamp()))

    set_auth_cookies(response, new_access_token, new_refresh_token)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(security)
    ] = None,
):
    presented = [request.cookies.get(name) for name in AUTH_COOKIES]
    if credentials:
        presented.append(credentials.credentials)
    for token in presented:
        if not token:
            continue
        payload = decode_token(token)
        if payload and payload.get("jti") and payload.get("exp"):
            ttl = int(payload["exp"] - utc_now().timestamp())
            await clear_token_grace(payload["jti"])
            await revoke_token(payload["jti"], ttl)
    clear_auth_cookies(response)
    return {"message": "Logged out"}


@router.get("/me", response_model=UserRead)
async def get_current_user_info(current_user: CurrentUser):
    return current_user


@router.post("/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    response: Response,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    await require_current_password(current_user, password_data.current_password)
    try:
        validate_password_strength(
            password_data.new_password,
            user_inputs=[current_user.email, current_user.username],
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e)
        ) from e

    current_user.hashed_password = await hash_password_async(password_data.new_password)
    current_user.updated_at = utc_now()

    session.add(current_user)
    await session.commit()
    await reissue_session(response, current_user)
    logger.info("password changed", user=str(current_user.id))

    return {
        "message": "Password changed",
        "user_id": str(current_user.id),
    }


@router.post("/change-username")
async def change_username(
    username_data: UsernameChangeRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    await require_current_password(current_user, username_data.current_password)
    existing_user = await session.scalar(
        select(User).where(User.username == username_data.new_username)
    )
    if existing_user and existing_user.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is taken",
        )

    previous = current_user.username
    current_user.username = username_data.new_username
    current_user.updated_at = utc_now()

    session.add(current_user)
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is taken",
        ) from e
    logger.info(
        "username changed",
        user=str(current_user.id),
        previous=previous,
        username=username_data.new_username,
    )

    return {
        "message": "Username changed",
        "user_id": str(current_user.id),
        "new_username": username_data.new_username,
    }
