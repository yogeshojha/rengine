from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import async_db_session, get_session
from app.core.ratelimit import is_token_revoked
from app.core.security import TOKEN_TYPE_ACCESS, decode_token
from shared.models.user import User

security = HTTPBearer(auto_error=False)

BEARER_HEADERS = {"WWW-Authenticate": "Bearer"}


async def get_token_from_request(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(security)
    ] = None,
) -> str:
    if credentials:
        return credentials.credentials

    from app.api.v1.auth import ACCESS_TOKEN_COOKIE  # noqa: PLC0415

    token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers=BEARER_HEADERS,
        )

    return token


async def resolve_user(token: str, session: AsyncSession) -> User:
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers=BEARER_HEADERS,
        )

    if payload.get("type") != TOKEN_TYPE_ACCESS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers=BEARER_HEADERS,
        )

    jti = payload.get("jti")
    if jti and await is_token_revoked(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
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

    return user


def ensure_active(user: User) -> User:
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is inactive",
        )
    return user


async def get_current_user(
    token: Annotated[str, Depends(get_token_from_request)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    return await resolve_user(token, session)


async def get_stream_user(
    token: Annotated[str, Depends(get_token_from_request)],
) -> User:
    async with async_db_session() as session:
        user = await resolve_user(token, session)
    return ensure_active(user)


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    return ensure_active(current_user)


async def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access is required",
        )
    return current_user


async def token_still_valid(token: str) -> bool:
    payload = decode_token(token)
    if payload is None or payload.get("type") != TOKEN_TYPE_ACCESS:
        return False
    jti = payload.get("jti")
    return not (jti and await is_token_revoked(jti))


CurrentUser = Annotated[User, Depends(get_current_active_user)]
StreamUser = Annotated[User, Depends(get_stream_user)]
CurrentSuperuser = Annotated[User, Depends(get_current_superuser)]
