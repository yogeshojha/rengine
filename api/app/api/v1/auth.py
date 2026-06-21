from datetime import timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import BEARER_HEADERS, CurrentSuperuser, CurrentUser
from app.config import settings
from app.core.database import get_session
from app.core.ratelimit import (
    clear_failures,
    is_token_revoked,
    record_failure,
    revoke_token,
    too_many_attempts,
)
from app.core.security import (
    TOKEN_TYPE_MFA,
    TOKEN_TYPE_REFRESH,
    create_access_token,
    create_refresh_token,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.utils.validation import validate_password_strength, validate_username
from shared.models.user import User, UserCreate, UserRead
from shared.schemas.auth import (
    LoginRequest,
    LoginResponse,
    PasswordChangeRequest,
    TokenResponse,
    UsernameChangeRequest,
)
from shared.utils.datetime import utc_now

_DUMMY_HASH = "$argon2id$v=19$m=65536,t=2,p=4$BFG/6RwwvAFTuluSmeDY5Q$ssCZOxGGhBFAM+3ub/t5TVPTUAyiL4Maz42kFYbcWts"

router = APIRouter(prefix="/auth", tags=["authentication"])

ACCESS_TOKEN_COOKIE = "access_token"  # noqa: S105
REFRESH_TOKEN_COOKIE = "refresh_token"  # noqa: S105


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
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    rl_key = f"auth:login:{login_data.username.lower()}"
    await too_many_attempts(rl_key, limit=10)

    result = await session.execute(
        select(User).where(User.username == login_data.username)
    )
    user = result.scalar_one_or_none()

    if not user:
        verify_password(login_data.password, _DUMMY_HASH)

    if not user or not verify_password(login_data.password, user.hashed_password):
        await record_failure(rl_key, window_seconds=900)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers=BEARER_HEADERS,
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    await clear_failures(rl_key)

    if user.totp_enabled:
        mfa_token = create_token(str(user.id), TOKEN_TYPE_MFA, timedelta(minutes=5))
        return LoginResponse(mfa_required=True, mfa_token=mfa_token)

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    set_auth_cookies(response, access_token, refresh_token)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=TokenResponse)
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

    jti = payload.get("jti")
    if jti and await is_token_revoked(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
            headers=BEARER_HEADERS,
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers=BEARER_HEADERS,
        )

    try:
        user_id = UUID(user_id_str)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers=BEARER_HEADERS,
        ) from e

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers=BEARER_HEADERS,
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    new_access_token = create_access_token(str(user.id))
    new_refresh_token = create_refresh_token(str(user.id))

    set_auth_cookies(response, new_access_token, new_refresh_token)

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
    )


@router.post("/logout")
async def logout(request: Request, response: Response):
    for cookie_name in (ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE):
        token = request.cookies.get(cookie_name)
        if not token:
            continue
        payload = decode_token(token)
        if payload and payload.get("jti") and payload.get("exp"):
            ttl = int(payload["exp"] - utc_now().timestamp())
            await revoke_token(payload["jti"], ttl)
    clear_auth_cookies(response)
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserRead)
async def get_current_user_info(current_user: CurrentUser):
    return current_user


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: UserCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: CurrentSuperuser,  # noqa: ARG001
):
    try:
        validate_username(user_in.username)
        validate_password_strength(
            user_in.password, user_inputs=[user_in.email, user_in.username]
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e

    result = await session.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    result = await session.execute(
        select(User).where(User.username == user_in.username)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this username already exists",
        )

    user = User(
        email=user_in.email,
        username=user_in.username,
        hashed_password=hash_password(user_in.password),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return user


@router.post("/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    validate_password_strength(password_data.new_password)

    target_user_id = password_data.user_id or current_user.id

    result = await session.execute(select(User).where(User.id == target_user_id))
    target_user = result.scalar_one_or_none()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if target_user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only change your own password",
        )

    if target_user_id == current_user.id:
        if not password_data.current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is required",
            )
        rl_key = f"auth:change-password:{current_user.id}"
        await too_many_attempts(rl_key, limit=5)
        if not verify_password(
            password_data.current_password, target_user.hashed_password
        ):
            await record_failure(rl_key, window_seconds=900)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect",
            )
        await clear_failures(rl_key)

    target_user.hashed_password = hash_password(password_data.new_password)
    target_user.updated_at = utc_now()

    session.add(target_user)
    await session.commit()

    return {
        "message": "Password changed successfully",
        "user_id": str(target_user_id),
    }


@router.post("/change-username")
async def change_username(
    username_data: UsernameChangeRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    validate_username(username_data.new_username)

    target_user_id = username_data.user_id or current_user.id

    result = await session.execute(select(User).where(User.id == target_user_id))
    target_user = result.scalar_one_or_none()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if target_user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only change your own username",
        )

    result = await session.execute(
        select(User).where(User.username == username_data.new_username)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user and existing_user.id != target_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    target_user.username = username_data.new_username
    target_user.updated_at = utc_now()

    session.add(target_user)
    await session.commit()

    return {
        "message": "Username changed successfully",
        "user_id": str(target_user_id),
        "new_username": username_data.new_username,
    }
