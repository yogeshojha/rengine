"""Text for postgres and for a reader: NUL is rejected outright, in text and in json alike."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.exc import StatementError

_NUL = "\x00"
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# asyncpg raises DBAPIError for a NUL; psycopg raises a bare ValueError while binding
REFUSED_ROW = (StatementError, ValueError)


def strip_nul(value: str) -> str:
    """Drop only what postgres refuses to store."""
    return value.replace(_NUL, "") if _NUL in value else value


def strip_control(value: str) -> str:
    """strip_nul plus the other control characters, for text a person reads back."""
    return _CTRL.sub("", value)


def scrub(value: Any) -> Any:
    """strip_nul through strings, lists and dicts on their way to a column."""
    if isinstance(value, str):
        return strip_nul(value)
    if isinstance(value, list):
        return [scrub(item) for item in value]
    if isinstance(value, dict):
        return {scrub(k): scrub(v) for k, v in value.items()}
    return value


def plural(count: int, word: str, many: str | None = None) -> str:
    """The form of a word that matches a count."""
    return word if count == 1 else (many or f"{word}s")


def counted(count: int, word: str, many: str | None = None) -> str:
    """A count and the form of its word that matches it."""
    return f"{count} {plural(count, word, many)}"
