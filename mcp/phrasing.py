"""Short spellings for a chat screen."""

from __future__ import annotations

from shared.utils.datetime import duration_text

SHORT_ID = 8


def short_id(value: object) -> str:
    return str(value)[:SHORT_ID]


def elapsed(seconds: float | None) -> str:
    return "" if seconds is None else duration_text(seconds)


def stamp(value) -> str:
    """Date and minute, from a datetime or an ISO string."""
    text = "" if value is None else str(value)
    return text[:16].replace("T", " ")


def number(value: int | None) -> str:
    return "" if value is None else f"{value:,}"
