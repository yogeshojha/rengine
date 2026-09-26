from __future__ import annotations

import logging

from fastapi import HTTPException, status

from shared.redis import async_client

logger = logging.getLogger(__name__)


async def too_many_attempts(key: str, *, limit: int) -> None:
    try:
        raw = await async_client().get(key)
    except Exception as exc:
        logger.warning("rate limiter read unavailable for %s: %s", key, exc)
        return
    if raw is not None and int(raw) >= limit:
        try:
            ttl = await async_client().ttl(key)
        except Exception:
            ttl = -1
        wait = f" Try again in {ttl} seconds." if ttl and ttl > 0 else ""
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many attempts.{wait}",
        )


async def record_failure(key: str, *, window_seconds: int) -> None:
    try:
        pipe = async_client().pipeline(transaction=True)
        pipe.incr(key)
        pipe.expire(key, window_seconds, nx=True)
        await pipe.execute()
    except Exception as exc:
        logger.warning("rate limiter write unavailable for %s: %s", key, exc)


async def clear_failures(key: str) -> None:
    try:
        await async_client().delete(key)
    except Exception as exc:
        logger.warning("rate limiter clear unavailable for %s: %s", key, exc)


async def revoke_token(jti: str, ttl_seconds: int) -> None:
    if ttl_seconds <= 0:
        return
    try:
        await async_client().set(f"revoked:jti:{jti}", "1", ex=ttl_seconds)
    except Exception as exc:
        logger.warning("token revoke unavailable for %s: %s", jti, exc)


async def is_token_revoked(jti: str) -> bool:
    try:
        return await async_client().exists(f"revoked:jti:{jti}") == 1
    except Exception as exc:
        logger.warning("token revoke check unavailable for %s: %s", jti, exc)
        return False


async def grant_token_grace(jti: str, ttl_seconds: int) -> None:
    """How long a rotated token stays usable."""
    if ttl_seconds <= 0:
        return
    try:
        await async_client().set(f"grace:jti:{jti}", "1", ex=ttl_seconds)
    except Exception as exc:
        logger.warning("token grace unavailable for %s: %s", jti, exc)


async def is_token_in_grace(jti: str) -> bool:
    try:
        return await async_client().exists(f"grace:jti:{jti}") == 1
    except Exception as exc:
        logger.warning("token grace check unavailable for %s: %s", jti, exc)
        return False


async def clear_token_grace(jti: str) -> None:
    try:
        await async_client().delete(f"grace:jti:{jti}")
    except Exception as exc:
        logger.warning("token grace clear unavailable for %s: %s", jti, exc)
