"""Turn a value the database refuses into a 400 rather than an unhandled 500."""

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError
from starlette.status import HTTP_400_BAD_REQUEST

from shared.logging import get_logger

logger = get_logger(__name__)

# SQLSTATE class 22 is the SQL standard's data exception class: the value supplied
# cannot be represented in the column it was sent to. It is never a server fault.
_DATA_EXCEPTION = "22"

_MESSAGES = {
    "22001": "A value in the request is longer than the field allows.",
    "22003": "A number in the request is outside the range the field allows.",
    "22021": "A value in the request contains a NUL byte, which cannot be stored.",
}
_FALLBACK = "A value in the request is not valid for the field it was sent to."


def _sqlstate(exc: DBAPIError) -> str | None:
    orig = exc.orig
    inner = getattr(orig, "__cause__", None) or orig
    state = getattr(inner, "sqlstate", None)
    return state if isinstance(state, str) else None


async def data_exception_handler(request: Request, exc: DBAPIError) -> JSONResponse:
    state = _sqlstate(exc)
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
