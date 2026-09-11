from __future__ import annotations

from typing import Any

_MAX_URL = 2000


def parse_ffuf_record(record: dict[str, Any]) -> dict[str, Any] | None:
    """One ffuf NDJSON hit. `input.FUZZ` is base64 in this mode, so `url` is the word."""
    url = record.get("url")
    status = record.get("status")
    if not isinstance(url, str) or not url or len(url) > _MAX_URL:
        return None
    if not isinstance(status, int):
        return None
    redirect = record.get("redirectlocation") or None
    return {
        "url": url,
        "status_code": status,
        "content_length": _number(record.get("length")),
        "words": _number(record.get("words")),
        "lines": _number(record.get("lines")),
        "content_type": (record.get("content-type") or None),
        "redirect_location": redirect if isinstance(redirect, str) else None,
        "host": record.get("host") or None,
    }


def _number(value) -> int | None:
    return value if isinstance(value, int) else None
