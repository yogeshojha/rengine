# safe converters

import uuid
from datetime import datetime
from typing import Any


def safe_str(value: Any, default: str = "") -> str:
    """Safely convert a value to a stripped string."""
    if value is None:
        return default
    s = str(value).strip()
    return s if s else default


def safe_int(value: Any, default: int | None = None) -> int | None:
    """Safely convert a value to int."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_datetime(value: Any) -> datetime | None:
    """Safely extract a datetime, returning None if not a datetime."""
    if isinstance(value, datetime):
        return value
    return None


def safe_list(value: Any) -> list:
    """Safely convert to list."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def safe_bool(value: Any, default: bool = False) -> bool:
    """Safely convert to bool."""
    if isinstance(value, bool):
        return value
    return default


def safe_str_list(raw: list | None) -> list[str]:
    """Coerce a list to list[str], filtering out None/empty values."""
    if not raw:
        return []
    return [str(v).strip() for v in raw if v is not None and str(v).strip()]


def strip_trailing_dot(value: str) -> str:
    """Remove trailing dot from string"""
    return value.rstrip(".")


def safe_uuid(value: uuid.UUID | str | None) -> uuid.UUID | None:
    """string IDs to UUID, pass through UUID and None."""
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(value)
