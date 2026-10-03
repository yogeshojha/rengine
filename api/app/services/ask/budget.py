"""Questions a user may ask in a day."""

from __future__ import annotations

import uuid

from shared.definitions.ask import QUESTIONS_PER_DAY
from shared.logging import get_logger
from shared.redis import async_client
from shared.services.ai import AIError
from shared.utils.datetime import utc_now

logger = get_logger(__name__)

KEY = "ask:day:{user_id}:{day}"
DAY_SECONDS = 86_400
COUNTER_DOWN = (
    "The question counter is unavailable. Check that the redis service is running."
)


async def over_daily(user_id: uuid.UUID) -> bool:
    """Count one question. AIError when the counter is unavailable."""
    day = utc_now().strftime("%Y%m%d")
    key = KEY.format(user_id=user_id, day=day)
    try:
        pipe = async_client().pipeline(transaction=True)
        pipe.incr(key)
        pipe.expire(key, DAY_SECONDS, nx=True)
        used, _ = await pipe.execute()
    except Exception as exc:
        logger.warning("ask daily budget unavailable", error=str(exc))
        raise AIError(COUNTER_DOWN) from exc
    return used > QUESTIONS_PER_DAY
