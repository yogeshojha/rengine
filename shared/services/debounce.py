"""A shared 'not again yet' latch."""

from __future__ import annotations

import redis

from shared.config import BaseAppSettings
from shared.logging import get_logger

logger = get_logger(__name__)

_client: redis.Redis | None = None


def _redis() -> redis.Redis:
    global _client  # noqa: PLW0603
    if _client is None:
        _client = redis.from_url(BaseAppSettings().redis_url)
    return _client


def claim(key: str, ttl_seconds: int) -> bool:
    """True for the first caller in the window."""
    try:
        return bool(_redis().set(f"debounce:{key}", "1", nx=True, ex=ttl_seconds))
    except Exception:
        logger.debug("debounce unavailable, proceeding", exc_info=True)
        return True
