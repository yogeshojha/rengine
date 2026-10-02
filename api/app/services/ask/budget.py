"""Questions a user may ask in a day."""

from __future__ import annotations

import uuid

from shared.definitions.ask import QUESTIONS_PER_DAY
from shared.logging import get_logger
from shared.redis import async_client
from shared.utils.datetime import utc_now

logger = get_logger(__name__)

KEY = "ask:day:{user_id}:{day}"
DAY_SECONDS = 86_400


async def over_daily(user_id: uuid.UUID) -> bool:
    day = utc_now().strftime("%Y%m%d")
    key = KEY.format(user_id=user_id, day=day)
    try:
        redis = async_client()
        used = await redis.incr(key)
        if used == 1:
            await redis.expire(key, DAY_SECONDS)
    except Exception as exc:
        logger.debug("ask daily budget skipped", error=str(exc))
        return False
    return used > QUESTIONS_PER_DAY
