from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import BEARER_HEADERS, CurrentUser, user_for_payload
from app.api.v1.auth import (
    LoginResponse,
    reissue_session,
    require_current_password,
    set_auth_cookies,
)
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
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.services.totp import TOTPService
from app.utils.validation import MAX_PASSWORD_LENGTH
from shared.definitions.auth import (
    OTP_DAILY_KEY,
    OTP_DAILY_LIMIT,
    OTP_DAILY_WINDOW,
    OTP_FAILURE_KEY,
    OTP_FAILURE_LIMIT,
    OTP_FAILURE_WINDOW,
)
from shared.logging import get_logger
from shared.models.user import User
from shared.utils.datetime import utc_now

logger = get_logger(__name__)

router = APIRouter(prefix="/auth/2fa", tags=["two-factor"])

UNREADABLE_DETAIL = "The stored two-factor secret is unreadable. Use a backup code."
MAX_CODE_LENGTH = 32
MAX_MFA_TOKEN_LENGTH = 2048


class TwoFactorCodeRequest(BaseModel):
    code: str = Field(max_length=MAX_CODE_LENGTH)


class TwoFactorSetupRequest(BaseModel):
    current_password: str = Field(max_length=MAX_PASSWORD_LENGTH)


class TwoFactorLoginRequest(BaseModel):
    mfa_token: str = Field(max_length=MAX_MFA_TOKEN_LENGTH)
    code: str = Field(max_length=MAX_CODE_LENGTH)


async def check_code_budget(user: User) -> None:
    await too_many_attempts(
        OTP_FAILURE_KEY.format(user_id=user.id),
        limit=OTP_FAILURE_LIMIT,
        fail_closed=True,
    )
    await too_many_attempts(
        OTP_DAILY_KEY.format(user_id=user.id),
        limit=OTP_DAILY_LIMIT,
        fail_closed=True,
    )


async def spend_code_budget(user: User) -> None:
    await record_failure(
        OTP_FAILURE_KEY.format(user_id=user.id), window_seconds=OTP_FAILURE_WINDOW
    )
    await record_failure(
        OTP_DAILY_KEY.format(user_id=user.id), window_seconds=OTP_DAILY_WINDOW
    )


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TOTPService:
    return TOTPService(session)


@router.get("/status")
async def status_2fa(current_user: CurrentUser):
    return {"enabled": current_user.totp_enabled}


@router.post("/setup")
async def setup_2fa(
    data: TwoFactorSetupRequest,
    current_user: CurrentUser,
    service: Annotated[TOTPService, Depends(get_service)],
):
    rl_key = f"auth:2fa-setup-start:{current_user.id}"
    await too_many_attempts(rl_key, limit=10, fail_closed=True)
    await record_failure(rl_key, window_seconds=300)
    await require_current_password(current_user, data.current_password)
    return await service.start_setup(current_user)


@router.post("/verify")
async def verify_2fa(
    data: TwoFactorCodeRequest,
    response: Response,
    current_user: CurrentUser,
    service: Annotated[TOTPService, Depends(get_service)],
):
    rl_key = f"auth:2fa-setup:{current_user.id}"
    await too_many_attempts(rl_key, limit=10, fail_closed=True)
    try:
        backup_codes = await service.verify_and_enable(current_user, data.code)
    except HTTPException:
        await record_failure(rl_key, window_seconds=300)
        raise
    except ValueError as e:
        await record_failure(rl_key, window_seconds=300)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The stored two-factor secret is unreadable. Start setup again.",
        ) from e
    await clear_failures(rl_key)
    await reissue_session(response, current_user)
    logger.info("two-factor enabled", user=str(current_user.id))
    return {"enabled": True, "backup_codes": backup_codes}


@router.post("/disable")
async def disable_2fa(
    data: TwoFactorCodeRequest,
    response: Response,
    current_user: CurrentUser,
    service: Annotated[TOTPService, Depends(get_service)],
):
    await check_code_budget(current_user)
    try:
        await service.disable(current_user, data.code)
    except HTTPException:
        await spend_code_budget(current_user)
        logger.warning("two-factor disable refused", user=str(current_user.id))
        raise
    except ValueError as e:
        await spend_code_budget(current_user)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=UNREADABLE_DETAIL,
        ) from e
    await clear_failures(OTP_FAILURE_KEY.format(user_id=current_user.id))
    await reissue_session(response, current_user)
    logger.info("two-factor disabled", user=str(current_user.id))
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

    jti = payload["jti"]
    if await is_token_revoked(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="MFA token has been used",
            headers=BEARER_HEADERS,
        )

    user = await user_for_payload(payload, session)
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers=BEARER_HEADERS,
        )

    await check_code_budget(user)

    try:
        code_valid = await service.verify_code(user, data.code)
    except ValueError as e:
        await spend_code_budget(user)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=UNREADABLE_DETAIL,
        ) from e

    if not code_valid:
        await spend_code_budget(user)
        logger.warning("second factor refused", user=str(user.id))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid verification code",
        )

    await clear_failures(OTP_FAILURE_KEY.format(user_id=user.id))
    await revoke_token(jti, int(payload["exp"] - utc_now().timestamp()))

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    set_auth_cookies(response, access_token, refresh_token)
    logger.info("login succeeded", user=str(user.id), second_factor=True)

    return LoginResponse()
