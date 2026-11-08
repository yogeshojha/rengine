"""Map a Postgres data exception to a 400 and a timeout to a 503."""

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_503_SERVICE_UNAVAILABLE

from shared.logging import get_logger
from shared.services.asset_query import TIMEOUT_SQLSTATE

logger = get_logger(__name__)

_DATA_EXCEPTION = "22"

_MESSAGES = {
    "22001": "A value in the request is longer than the field allows.",
    "22003": "A number in the request is outside the range the field allows.",
    "22021": "A value in the request contains a NUL byte.",
}
_FALLBACK = "A value in the request is not valid for its field."
_TIMEOUT = "The query timed out. Narrow the filter and try again."


def _sqlstate(exc: DBAPIError) -> str | None:
    orig = exc.orig
    inner = getattr(orig, "__cause__", None) or orig
    state = getattr(inner, "sqlstate", None)
    return state if isinstance(state, str) else None


async def timeout_handler(request: Request, _exc: TimeoutError) -> JSONResponse:
    from app.core.database import DATABASE_UNAVAILABLE  # noqa: PLC0415

    logger.warning(
        "database call timed out", path=request.url.path, method=request.method
    )
    return JSONResponse(
        status_code=HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": DATABASE_UNAVAILABLE},
    )


async def data_exception_handler(request: Request, exc: DBAPIError) -> JSONResponse:
    state = _sqlstate(exc)
    if state == TIMEOUT_SQLSTATE:
        logger.warning(
            "statement timed out", path=request.url.path, method=request.method
        )
        return JSONResponse(
            status_code=HTTP_503_SERVICE_UNAVAILABLE, content={"detail": _TIMEOUT}
        )
    if not state or not state.startswith(_DATA_EXCEPTION):
        raise exc
    logger.info(
        "rejected unstorable value",
        path=request.url.path,
        method=request.method,
        sqlstate=state,
    )
    return JSONResponse(
        status_code=HTTP_400_BAD_REQUEST,
        content={"detail": _MESSAGES.get(state, _FALLBACK)},
    )
