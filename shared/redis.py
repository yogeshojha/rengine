"""One Redis connection per process and instance: state on one, cached aggregates on the other."""

from __future__ import annotations

import redis
import redis.asyncio as aioredis

from shared.config import base_settings

CACHE_TIMEOUT_SECONDS = 3.0

_async: aioredis.Redis | None = None
_sync: redis.Redis | None = None
_cache: aioredis.Redis | None = None


def async_client() -> aioredis.Redis:
    global _async  # noqa: PLW0603
    if _async is None:
        _async = aioredis.from_url(base_settings().redis_url, decode_responses=True)
    return _async


def sync_client() -> redis.Redis:
    global _sync  # noqa: PLW0603
    if _sync is None:
        _sync = redis.from_url(base_settings().redis_url, decode_responses=True)
    return _sync


def cache_client() -> aioredis.Redis:
    """Client of the evicting instance, where a written key may be gone on the next read."""
    global _cache  # noqa: PLW0603
    if _cache is None:
        _cache = aioredis.from_url(
            base_settings().redis_cache_url,
            decode_responses=True,
            socket_connect_timeout=CACHE_TIMEOUT_SECONDS,
            socket_timeout=CACHE_TIMEOUT_SECONDS,
        )
    return _cache
