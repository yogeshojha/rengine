"""A shared 'not again yet' latch."""

from __future__ import annotations

from shared.logging import get_logger
from shared.redis import sync_client

logger = get_logger(__name__)


def claim(key: str, ttl_seconds: int) -> bool:
    """True for the first caller in the window."""
    try:
        return bool(sync_client().set(f"debounce:{key}", "1", nx=True, ex=ttl_seconds))
    except Exception:
        logger.debug("debounce unavailable, proceeding", exc_info=True)
        return True
