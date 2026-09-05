"""Text stored in postgres: NUL is rejected outright, in text and in json alike."""

from __future__ import annotations

import re
from typing import Any

_NUL = "\x00"
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def strip_nul(value: str) -> str:
    """Drop only what postgres refuses to store; a captured response body is not text."""
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
