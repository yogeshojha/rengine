import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings
from app.core.client_ip import client_id
from app.core.ratelimit import _client

logger = logging.getLogger(__name__)

_EXEMPT_PREFIXES = ("/api/v1/events", "/api/v1/media")


class GlobalRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        limit = settings.GLOBAL_RATE_LIMIT_PER_MINUTE
        path = request.url.path
        if (
            limit <= 0
            or request.method == "OPTIONS"
            or any(path.startswith(p) for p in _EXEMPT_PREFIXES)
        ):
            return await call_next(request)

        bucket = int(time.time() // 60)
        key = f"throttle:{client_id(request)}:{bucket}"
        try:
            pipe = _client().pipeline(transaction=True)
            pipe.incr(key)
            pipe.expire(key, 60, nx=True)
            count, _ = await pipe.execute()
        except Exception as exc:
            logger.warning("global rate limiter unavailable: %s", exc)
            return await call_next(request)

        if count > limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again in a minute."},
                headers={"Retry-After": str(60 - int(time.time() % 60))},
            )
        return await call_next(request)
