import uuid
from datetime import datetime
from typing import Any


def safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    s = str(value).strip()
    return s if s else default


def safe_int(value: Any, default: int | None = None) -> int | None:
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    return None


def safe_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    return default


def safe_str_list(raw: list | None) -> list[str]:
    if not raw:
        return []
    return [str(v).strip() for v in raw if v is not None and str(v).strip()]


def strip_trailing_dot(value: str) -> str:
    return value.rstrip(".")


def safe_uuid(value: uuid.UUID | str | None) -> uuid.UUID | None:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(value)
