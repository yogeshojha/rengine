from __future__ import annotations

from typing import Any

_MAX_METHOD = 10


def parse_katana_record(record: dict[str, Any]) -> dict[str, Any] | None:
    """Flatten one katana JSONL record into url, referrer, method and tag."""
    request = record.get("request") or {}
    url = request.get("endpoint") or record.get("endpoint") or record.get("url")
    if not isinstance(url, str) or not url:
        return None
    response = record.get("response") or {}
    method = request.get("method")
    status = response.get("status_code")
    return {
        "url": url,
        "found_on": request.get("source") or None,
        "method": method[:_MAX_METHOD].upper() if isinstance(method, str) else None,
        "tag": request.get("tag") or None,
        "attribute": request.get("attribute") or None,
        "status_code": status if isinstance(status, int) else None,
        "content_type": _header(response, "content_type"),
        "content_length": response.get("content_length"),
        "title": response.get("title") or None,
    }


def _header(response: dict, key: str) -> str | None:
    value = (response.get("headers") or {}).get(key)
    return value if isinstance(value, str) and value else None
