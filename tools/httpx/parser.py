from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from shared.services.scan_resolve import MASK
from shared.utils.datetime import utc_now
from tools.runner.fieldmap import F, parse_record

# mask scan-context auth headers the scanner injected (same contract as command redaction)
_REQUEST_SECRET_HEADER = re.compile(
    r"(?im)^((?:authorization|proxy-authorization|cookie|x-api-key|"
    r"[\w-]*(?:token|secret|api-?key)[\w-]*)\s*:\s*).+$"
)


def _redact_request(value: Any) -> str | None:
    if not value or not isinstance(value, str):
        return None
    return _REQUEST_SECRET_HEADER.sub(rf"\1{MASK}", value)


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value if v]
    return [str(value)] if value else []


def _first(value: Any) -> str | None:
    if isinstance(value, list):
        return str(value[0]) if value else None
    return str(value) if value else None


def _asn_number(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    try:
        return int(str(value).upper().replace("AS", "").strip())
    except (TypeError, ValueError):
        return None


def _parse_dt(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt


def _seconds(value: Any) -> float | None:
    text = str(value).strip()
    try:
        if text.endswith("ms"):
            return round(float(text[:-2]) / 1000, 4)
        if text.endswith("s"):
            return round(float(text[:-1]), 4)
        return round(float(text), 4)
    except ValueError:
        return None


def _host_of(record: dict) -> str:
    raw = (record.get("input") or record.get("url") or "").strip()
    if "://" in raw:
        raw = raw.split("://", 1)[1]
    return raw.split("/", 1)[0].rsplit(":", 1)[0].strip().lower()


def _tls_expired(record: dict) -> bool | None:
    not_after = _parse_dt((record.get("tls") or {}).get("not_after"))
    return not_after < utc_now() if not_after else None


def _tls_self_signed(record: dict) -> bool | None:
    tls = record.get("tls") or {}
    issuer, subject = tls.get("issuer_dn"), tls.get("subject_dn")
    return issuer == subject if (issuer and subject) else None


HTTPX_FIELDS: dict[str, F] = {
    "url": F(lambda r: r.get("url") or r.get("input") or "", max_len=2000),
    "final_url": F("final_url", max_len=2000),
    "host": F(_host_of, max_len=500),
    "ip": F(lambda r: r.get("host_ip") or _first(r.get("a")), max_len=45),
    "a_records": F(lambda r: _str_list(r.get("a"))),
    "aaaa_records": F(lambda r: _str_list(r.get("aaaa"))),
    "port": F("port", _int),
    "scheme": F("scheme", str, max_len=8),
    "method": F("method", str, max_len=10),
    "path": F("path", str, max_len=2000),
    "status_code": F("status_code", _int),
    "chain_status_codes": F(lambda r: list(r.get("chain_status_codes") or [])),
    "title": F("title", str, max_len=1000),
    "webserver": F("webserver", str, max_len=255),
    "content_type": F("content_type", str, max_len=255),
    "content_length": F("content_length", _int),
    "location": F("location", str, max_len=2000),
    "response_time": F("time", _seconds),
    "words": F("words", _int),
    "lines": F("lines", _int),
    "tech": F(lambda r: _str_list(r.get("tech"))),
    "cpe": F(lambda r: list(r.get("cpe") or [])),
    "cname": F(lambda r: _first(r.get("cname")), max_len=500),
    "is_cdn": F(lambda r: bool(r.get("cdn"))),
    "cdn_name": F("cdn_name", str, max_len=100),
    "cdn_type": F("cdn_type", str, max_len=20),
    "supports_http2": F(lambda r: bool(r.get("http2"))),
    "supports_pipeline": F(lambda r: bool(r.get("pipeline"))),
    "jarm": F("jarm_hash", str, max_len=64),
    "favicon_hash": F("favicon", str, max_len=64),
    "favicon_path": F("favicon_path", str, max_len=2000),
    "content_hash": F("hash.body_sha256", str, max_len=80),
    "header_hash": F("hash.header_sha256", str, max_len=80),
    "tls_version": F("tls.tls_version", str, max_len=20),
    "tls_cipher": F("tls.cipher", str, max_len=100),
    "tls_subject_cn": F("tls.subject_cn", str, max_len=500),
    "tls_subject_dn": F("tls.subject_dn", str, max_len=1000),
    "tls_sans": F(lambda r: _str_list((r.get("tls") or {}).get("subject_an"))),
    "tls_issuer": F(lambda r: (r.get("tls") or {}).get("issuer_dn"), max_len=500),
    "tls_issuer_cn": F("tls.issuer_cn", str, max_len=500),
    "tls_issuer_org": F(
        lambda r: _first((r.get("tls") or {}).get("issuer_org")), max_len=500
    ),
    "tls_serial": F("tls.serial", str, max_len=200),
    "tls_fingerprint": F("tls.fingerprint_hash.sha256", str, max_len=80),
    "tls_not_before": F("tls.not_before", _parse_dt),
    "tls_not_after": F("tls.not_after", _parse_dt),
    "tls_expired": F(_tls_expired),
    "tls_self_signed": F(_tls_self_signed),
    "asn": F("asn.as_number", _asn_number),
    "asn_org": F("asn.as_name", str, max_len=255),
    "raw_request": F(lambda r: _redact_request(r.get("request")), max_len=65536),
    "raw_response_header": F("raw_header", str, max_len=65536),
    "response_headers": F(lambda r: r.get("header") or {}),
    "response_body": F("body", str, max_len=131072),
    "body_preview": F("body_preview", str, max_len=512),
}


def parse_httpx_record(record: dict) -> dict[str, Any]:
    return parse_record(record, HTTPX_FIELDS)
