"""Report a rejected request body without echoing the body back."""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY


def _part(value: object) -> str | int:
    return value if isinstance(value, str | int) else str(value)


async def validation_error_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    # FastAPI's default puts the offending value in `input`, and encoding a deeply
    # nested one exhausts the stack while building the 422 itself.
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
