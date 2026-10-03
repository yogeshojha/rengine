"""Refuse a request body over the size cap."""

from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from starlette.status import HTTP_413_CONTENT_TOO_LARGE
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import API_V1_PREFIX

MAX_REQUEST_BYTES = 128 * 1024 * 1024
TOO_LARGE = f"The request body is larger than the {MAX_REQUEST_BYTES // (1024 * 1024)} MB limit."
AUTH_PREFIX = f"{API_V1_PREFIX}/auth/"
MAX_AUTH_REQUEST_BYTES = 64 * 1024
AUTH_TOO_LARGE = (
    f"The request body is larger than the {MAX_AUTH_REQUEST_BYTES // 1024} KB limit."
)


def _cap(scope: Scope) -> tuple[int, str]:
    if scope.get("path", "").startswith(AUTH_PREFIX):
        return MAX_AUTH_REQUEST_BYTES, AUTH_TOO_LARGE
    return MAX_REQUEST_BYTES, TOO_LARGE


def _declared_length(scope: Scope) -> int | None:
    for name, value in scope.get("headers", ()):
        if name == b"content-length":
            try:
                return int(value)
            except ValueError:
                return None
    return None


class BodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        limit, detail = _cap(scope)
        declared = _declared_length(scope)
        if declared is not None and declared > limit:
            response = JSONResponse(
                status_code=HTTP_413_CONTENT_TOO_LARGE, content={"detail": detail}
            )
            await response(scope, receive, send)
            return
        received = 0

        async def capped() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    raise HTTPException(
                        status_code=HTTP_413_CONTENT_TOO_LARGE, detail=detail
                    )
            return message

        await self.app(scope, capped, send)
