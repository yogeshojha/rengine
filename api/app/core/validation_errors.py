"""Validation errors without the echoed input."""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.status import HTTP_422_UNPROCESSABLE_CONTENT


def _part(value: object) -> str | int:
    return value if isinstance(value, str | int) else str(value)


def validation_detail(loc: list[str | int], msg: str) -> list[dict]:
    """A 422 detail in the request validation shape."""
    return [{"loc": loc, "msg": msg, "type": "value_error"}]


def detail_text(detail: object) -> str:
    """A refusal's wording from a string or a listed detail."""
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        return " ".join(
            str(item["msg"])
            for item in detail
            if isinstance(item, dict) and item.get("msg")
        )
    return ""


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
        status_code=HTTP_422_UNPROCESSABLE_CONTENT, content={"detail": detail}
    )
