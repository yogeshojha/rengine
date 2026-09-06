from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import BEARER_HEADERS, CurrentUser
from app.api.v1.auth import set_auth_cookies
from app.core.database import get_session
from app.core.ratelimit import clear_failures, record_failure, too_many_attempts
from app.core.security import (
    TOKEN_TYPE_MFA,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.services.totp import TOTPService
from shared.models.user import User
from shared.schemas.auth import LoginResponse, TwoFactorLoginRequest

router = APIRouter(prefix="/auth/2fa", tags=["two-factor"])


class TwoFactorCodeRequest(BaseModel):
    code: str


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TOTPService:
    return TOTPService(session)


@router.get("/status")
async def status_2fa(current_user: CurrentUser):
    return {"enabled": current_user.totp_enabled}


@router.post("/setup")
async def setup_2fa(
    current_user: CurrentUser,
    service: Annotated[TOTPService, Depends(get_service)],
):
    rl_key = f"auth:2fa-setup-start:{current_user.id}"
    await too_many_attempts(rl_key, limit=10)
    await record_failure(rl_key, window_seconds=300)
    return await service.start_setup(current_user)


@router.post("/verify")
async def verify_2fa(
    data: TwoFactorCodeRequest,
    current_user: CurrentUser,
    service: Annotated[TOTPService, Depends(get_service)],
):
    rl_key = f"auth:2fa-setup:{current_user.id}"
    await too_many_attempts(rl_key, limit=10)
    try:
        backup_codes = await service.verify_and_enable(current_user, data.code)
    except HTTPException:
        await record_failure(rl_key, window_seconds=300)
        raise
    except ValueError as e:
        await record_failure(rl_key, window_seconds=300)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The stored two-factor secret is unreadable. Disable two-factor and enroll again.",
        ) from e
    await clear_failures(rl_key)
    return {"enabled": True, "backup_codes": backup_codes}


@router.post("/disable")
async def disable_2fa(
    data: TwoFactorCodeRequest,
    current_user: CurrentUser,
    service: Annotated[TOTPService, Depends(get_service)],
):
    rl_key = f"auth:2fa-disable:{current_user.id}"
    await too_many_attempts(rl_key, limit=10)
    try:
        await service.disable(current_user, data.code)
    except HTTPException:
        await record_failure(rl_key, window_seconds=300)
        raise
    except ValueError as e:
        await record_failure(rl_key, window_seconds=300)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The stored two-factor secret is unreadable. Disable two-factor and enroll again.",
        ) from e
    await clear_failures(rl_key)
    return {"enabled": False}


@router.post("/login", response_model=LoginResponse)
async def login_2fa(
    data: TwoFactorLoginRequest,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[TOTPService, Depends(get_service)],
):
    payload = decode_token(data.mfa_token)
    if payload is None or payload.get("type") != TOKEN_TYPE_MFA:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired MFA token",
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

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers=BEARER_HEADERS,
        )

    rl_key = f"auth:2fa:{user.id}"
    await too_many_attempts(rl_key, limit=5)

    try:
        code_valid = await service.verify_code(user, data.code)
    except ValueError:
        code_valid = False

    if not code_valid:
        await record_failure(rl_key, window_seconds=300)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid verification code",
        )

    await clear_failures(rl_key)

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    set_auth_cookies(response, access_token, refresh_token)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )
