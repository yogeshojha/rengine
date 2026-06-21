import logging

import redis.asyncio as aioredis
from fastapi import HTTPException, status

from app.config import settings

logger = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None


def _client() -> aioredis.Redis:
    global _redis  # noqa: PLW0603
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def too_many_attempts(key: str, *, limit: int) -> None:
    try:
        raw = await _client().get(key)
    except Exception as exc:
        logger.warning("rate limiter read unavailable for %s: %s", key, exc)
        return
    if raw is not None and int(raw) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Please wait a moment and try again.",
        )


async def record_failure(key: str, *, window_seconds: int) -> None:
    try:
        pipe = _client().pipeline(transaction=True)
        pipe.incr(key)
        pipe.expire(key, window_seconds, nx=True)
        await pipe.execute()
    except Exception as exc:
        logger.warning("rate limiter write unavailable for %s: %s", key, exc)


async def clear_failures(key: str) -> None:
    try:
        await _client().delete(key)
    except Exception as exc:
        logger.warning("rate limiter clear unavailable for %s: %s", key, exc)


async def revoke_token(jti: str, ttl_seconds: int) -> None:
    if ttl_seconds <= 0:
        return
    try:
        await _client().set(f"revoked:jti:{jti}", "1", ex=ttl_seconds)
    except Exception as exc:
        logger.warning("token revoke unavailable for %s: %s", jti, exc)


async def is_token_revoked(jti: str) -> bool:
    try:
        return await _client().exists(f"revoked:jti:{jti}") == 1
    except Exception as exc:
        logger.warning("token revoke check unavailable for %s: %s", jti, exc)
        return False
