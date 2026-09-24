"""Which workers serve the scan queues, as a Redis key per worker with a TTL."""

import redis

from app.config import settings
from shared.logging import get_logger

logger = get_logger(__name__)

ANNOUNCE_SECONDS = 30.0
PRESENCE_TTL = int(ANNOUNCE_SECONDS * 3)
_PREFIX = "rengine:scan-worker:"

_client: redis.Redis | None = None


def _redis() -> redis.Redis:
    global _client  # noqa: PLW0603
    if _client is None:
        _client = redis.from_url(settings.celery_broker_url)
    return _client


def announce(hostname: str) -> None:
    try:
        _redis().set(f"{_PREFIX}{hostname}", "1", ex=PRESENCE_TTL)
    except Exception:
        logger.warning("worker presence not written", exc_info=True)


def withdraw(hostname: str) -> None:
    try:
        _redis().delete(f"{_PREFIX}{hostname}")
    except Exception:
        logger.warning("worker presence not removed", exc_info=True)


def live_workers() -> set[str] | None:
    """Hostnames of the scan workers seen within the TTL, or None when Redis is unreadable."""
    try:
        keys = _redis().keys(f"{_PREFIX}*")
    except Exception:
        logger.warning("worker presence unreadable", exc_info=True)
        return None
    return {key.decode()[len(_PREFIX) :] for key in keys}
