"""Refuse a request body over the size cap."""

from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from starlette.status import HTTP_413_CONTENT_TOO_LARGE
from starlette.types import ASGIApp, Message, Receive, Scope, Send

MAX_REQUEST_BYTES = 128 * 1024 * 1024
TOO_LARGE = f"The request body is larger than the {MAX_REQUEST_BYTES // (1024 * 1024)} MB limit."


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
        declared = _declared_length(scope)
        if declared is not None and declared > MAX_REQUEST_BYTES:
            response = JSONResponse(
                status_code=HTTP_413_CONTENT_TOO_LARGE, content={"detail": TOO_LARGE}
            )
            await response(scope, receive, send)
            return
        received = 0

        async def capped() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > MAX_REQUEST_BYTES:
                    raise HTTPException(
                        status_code=HTTP_413_CONTENT_TOO_LARGE, detail=TOO_LARGE
                    )
            return message

        await self.app(scope, capped, send)
