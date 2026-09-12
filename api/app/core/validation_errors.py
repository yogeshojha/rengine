"""Validation errors without the echoed input."""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY


def _part(value: object) -> str | int:
    return value if isinstance(value, str | int) else str(value)


async def validation_error_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    detail = [
        {
            "type": str(error.get("type", "")),
            "loc": [_part(part) for part in error.get("loc", ())],
            "msg": str(error.get("msg", "")),
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": detail}
    )
