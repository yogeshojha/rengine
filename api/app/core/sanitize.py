"""Reject request input the database cannot store before it reaches a query."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_400_BAD_REQUEST

# Postgres rejects NUL in text, so a parameter carrying one fails while binding and
# surfaces as a 500. It is never meaningful in a URL.
_NUL = "\x00"


class RejectNulMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        query = request.url.query
        if query and (_NUL in query or "%00" in query.lower()):
            return JSONResponse(
                status_code=HTTP_400_BAD_REQUEST,
                content={"detail": "Query parameters must not contain NUL bytes."},
            )
        return await call_next(request)
