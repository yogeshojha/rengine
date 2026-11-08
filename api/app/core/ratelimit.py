import logging
import time
from uuid import UUID

from fastapi import HTTPException, status

from app.config import settings
from shared.definitions.auth import LOGIN_ACCOUNT_KEY
from shared.redis import (
    StateUnavailableError,
    async_client,
    state_available,
    state_failed,
)

logger = logging.getLogger(__name__)


LIMITER_UNAVAILABLE = (
    "The rate limiter is unavailable. Check that the redis service is running."
)

SESSIONS_UNAVAILABLE = (
    "Sessions cannot be checked. Check that the redis service is running."
)


def _state():
    if not state_available():
        raise StateUnavailableError
    return async_client()


async def too_many_attempts(key: str, *, limit: int, fail_closed: bool = False) -> None:
    try:
        raw = await _state().get(key)
    except Exception as exc:
        state_failed(exc)
        logger.warning("rate limiter read unavailable for %s: %s", key, exc)
        if fail_closed:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=LIMITER_UNAVAILABLE,
            ) from exc
        return
    if raw is not None and int(raw) >= limit:
        try:
            ttl = await _state().ttl(key)
        except Exception as exc:
            state_failed(exc)
            ttl = -1
        wait = f" Try again in {ttl} seconds." if ttl and ttl > 0 else ""
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many attempts.{wait}",
        )


async def record_failure(key: str, *, window_seconds: int) -> None:
    try:
        pipe = _state().pipeline(transaction=True)
        pipe.incr(key)
        pipe.expire(key, window_seconds, nx=True)
        await pipe.execute()
    except Exception as exc:
        state_failed(exc)
        logger.warning("rate limiter write unavailable for %s: %s", key, exc)


async def clear_failures(key: str) -> None:
    try:
        await _state().delete(key)
    except Exception as exc:
        state_failed(exc)
        logger.warning("rate limiter clear unavailable for %s: %s", key, exc)


async def clear_login_failures(username: str) -> bool:
    """Clear the account's login failures from every client address."""
    pattern = LOGIN_ACCOUNT_KEY.format(username=username.lower(), address="*")
    try:
        client = _state()
        keys = [key async for key in client.scan_iter(match=pattern)]
        if keys:
            await client.delete(*keys)
    except Exception as exc:
        state_failed(exc)
        logger.warning("login failure clear unavailable for %s: %s", username, exc)
        return False
    return True


async def revoke_token(jti: str, ttl_seconds: int) -> None:
    if ttl_seconds <= 0:
        return
    try:
        await _state().set(f"revoked:jti:{jti}", "1", ex=ttl_seconds)
    except Exception as exc:
        state_failed(exc)
        logger.warning("token revoke unavailable for %s: %s", jti, exc)


async def is_token_revoked(jti: str) -> bool:
    try:
        return await _state().exists(f"revoked:jti:{jti}") == 1
    except Exception as exc:
        state_failed(exc)
        logger.warning("token revoke check unavailable for %s: %s", jti, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=SESSIONS_UNAVAILABLE,
        ) from exc


async def grant_token_grace(jti: str, ttl_seconds: int) -> None:
    """How long a rotated token stays usable, counted from its first rotation."""
    if ttl_seconds <= 0:
        return
    try:
        await _state().set(f"grace:jti:{jti}", "1", ex=ttl_seconds, nx=True)
    except Exception as exc:
        state_failed(exc)
        logger.warning("token grace unavailable for %s: %s", jti, exc)


async def is_token_in_grace(jti: str) -> bool:
    try:
        return await _state().exists(f"grace:jti:{jti}") == 1
    except Exception as exc:
        state_failed(exc)
        logger.warning("token grace check unavailable for %s: %s", jti, exc)
        return False


async def clear_token_grace(jti: str) -> None:
    try:
        await _state().delete(f"grace:jti:{jti}")
    except Exception as exc:
        state_failed(exc)
        logger.warning("token grace clear unavailable for %s: %s", jti, exc)


async def revoke_user_tokens(user_id: UUID) -> bool:
    """Refuse every token issued to the user before this millisecond."""
    try:
        await _state().set(
            f"auth:valid-after:{user_id}",
            time.time_ns() // 1_000_000,
            ex=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        )
    except Exception as exc:
        state_failed(exc)
        logger.warning("session revoke unavailable for %s: %s", user_id, exc)
        return False
    return True


async def tokens_valid_after(user_id: UUID) -> int | None:
    try:
        raw = await _state().get(f"auth:valid-after:{user_id}")
    except Exception as exc:
        state_failed(exc)
        logger.warning("session revoke check unavailable for %s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=SESSIONS_UNAVAILABLE,
        ) from exc
    return int(raw) if raw is not None else None
