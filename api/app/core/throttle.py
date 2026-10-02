import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import API_V1_PREFIX, settings
from app.core.client_ip import client_id
from app.core.security import ACCESS_TOKEN_COOKIE, TOKEN_TYPE_ACCESS, decode_token
from shared.redis import async_client

logger = logging.getLogger(__name__)

_EXEMPT_PREFIXES = tuple(f"{API_V1_PREFIX}{p}" for p in ("/events", "/media"))
_BEARER = "bearer "


def _session_user(token: str | None) -> str | None:
    payload = decode_token(token) if token else None
    if not payload or payload.get("type") != TOKEN_TYPE_ACCESS:
        return None
    sub = payload.get("sub")
    return sub if isinstance(sub, str) and sub else None


def throttle_identity(request: Request) -> str:
    """The signed-in user a valid access token names, else the client address."""
    header = request.headers.get("authorization", "")
    bearer = (
        header[len(_BEARER) :].strip() if header.lower().startswith(_BEARER) else None
    )
    for token in (bearer, request.cookies.get(ACCESS_TOKEN_COOKIE)):
        user = _session_user(token)
        if user:
            return f"user:{user}"
    return f"ip:{client_id(request)}"


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
        try:
            key = f"throttle:{throttle_identity(request)}:{bucket}"
            pipe = async_client().pipeline(transaction=True)
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
