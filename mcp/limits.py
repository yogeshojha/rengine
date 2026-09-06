"""Per-token call ceiling. Fail-open: if Redis is down the agent still works."""

from __future__ import annotations

import uuid

from shared.logging import get_logger

logger = get_logger(__name__)

KEY = "mcp:rate:{token_id}"
WINDOW = 60


async def exceeded(token_id: uuid.UUID, limit: int) -> bool:
    from app.core.ratelimit import _client  # noqa: PLC0415

    key = KEY.format(token_id=token_id)
    try:
        redis = _client()
        used = await redis.incr(key)
        if used == 1:
            await redis.expire(key, WINDOW)
    except Exception as exc:
        logger.debug("mcp rate limit skipped", error=str(exc))
        return False
    return used > limit
