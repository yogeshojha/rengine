"""Normalize raw httpx JSON records into HttpAsset-ready field dicts."""

from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlsplit


def _int(value) -> int | None:
    return value if isinstance(value, int) else None


def _trunc(value, length: int) -> str | None:
    if value is None or value == "":
        return None
    return str(value)[:length]


def _asn_number(value) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    try:
        return int(str(value).upper().replace("AS", "").strip())
    except ValueError:
        return None


def _parse_dt(value) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt


def _host_of(record: dict) -> str:
    url = record.get("url") or ""
    host = urlsplit(url).hostname if url else None
    if host:
        return host
    return (record.get("input") or "").split(":")[0]


def parse_httpx_record(record: dict) -> dict:
    """Map one httpx JSON record to HttpAsset field names."""
    asn = record.get("asn") or {}
    tls = record.get("tls") or {}
    body_hash = record.get("hash")
    if isinstance(body_hash, dict):
        content_hash = body_hash.get("body_sha256") or body_hash.get("sha256")
    else:
        content_hash = body_hash
    cname = record.get("cname")
    cname_val = cname[0] if isinstance(cname, list) and cname else cname

    return {
        "url": record.get("url") or record.get("input") or "",
        "host": _host_of(record),
        "ip": _trunc(record.get("host"), 45),
        "port": _int(record.get("port")) or 0,
        "scheme": (record.get("scheme") or "https")[:8],
        "status_code": _int(record.get("status_code")),
        "title": _trunc(record.get("title"), 1000),
        "webserver": _trunc(record.get("webserver"), 255),
        "content_length": _int(record.get("content_length")),
        "content_type": _trunc(record.get("content_type"), 255),
        "location": _trunc(record.get("location"), 2000),
        "tech": list(record.get("tech") or []),
        "cname": _trunc(cname_val, 500),
        "asn": _asn_number(asn.get("as_number")),
        "asn_org": _trunc(asn.get("as_name"), 255),
        "is_cdn": bool(record.get("cdn")),
        "cdn_name": _trunc(record.get("cdn_name"), 100),
        "jarm": _trunc(record.get("jarm"), 64),
        "favicon_hash": _trunc(record.get("favicon"), 64),
        "content_hash": _trunc(content_hash, 80),
        "tls_issuer": _trunc(tls.get("issuer_dn") or tls.get("issuer_cn"), 500),
        "tls_subject_cn": _trunc(tls.get("subject_cn"), 500),
        "tls_sans": list(tls.get("subject_an") or []),
        "tls_not_after": _parse_dt(tls.get("not_after")),
        "tls_self_signed": tls.get("self_signed"),
        "tls_expired": tls.get("expired"),
        "tls_version": _trunc(tls.get("tls_version") or tls.get("version"), 20),
        "screenshot_path": _trunc(record.get("screenshot_path"), 500),
    }
