from __future__ import annotations

import ipaddress
import re
from datetime import datetime, timedelta

from shared.definitions.asset_query import MAX_NUMBER, FieldType
from shared.utils.datetime import utc_now

from .ast import QuerySyntaxError

_BYTES = {"b": 1, "kb": 1024, "k": 1024, "mb": 1024**2, "m": 1024**2, "gb": 1024**3}
_SECONDS = {"ms": 0.001, "s": 1.0, "m": 60.0, "h": 3600.0}
_RELATIVE = {"m": 60, "h": 3600, "d": 86400, "w": 604800, "mo": 2592000, "y": 31536000}
_SIZE_RE = re.compile(r"^(-?\d+(?:\.\d+)?)\s*([a-z]*)$", re.IGNORECASE)
_RELATIVE_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*(mo|[mhdwy])$", re.IGNORECASE)
_DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y")
_STATUS_CLASS_RE = re.compile(r"^([1-5])xx$", re.IGNORECASE)
_ASN_RE = re.compile(r"^as(\d+)$", re.IGNORECASE)


def _fail(raw: str, expected: str, start: int, end: int):
    msg = f"{raw!r} is not a valid {expected}."
    return QuerySyntaxError(msg, start, end)


def scaled_number(raw: str, kind: FieldType, start: int, end: int) -> float:
    match = _SIZE_RE.match(raw.strip())
    if match is None:
        raise _fail(raw, "number", start, end)
    amount = float(match.group(1))
    unit = match.group(2).lower()
    if unit:
        table = _BYTES if kind is FieldType.BYTES else _SECONDS
        if unit not in table:
            raise _fail(raw, "number", start, end)
        amount *= table[unit]
    return _bounded(amount, raw, start, end)


def _bounded(amount: float, raw: str, start: int, end: int) -> float:
    if abs(amount) > MAX_NUMBER:
        msg = f"{raw!r} is out of range."
        raise QuerySyntaxError(msg, start, end)
    return amount


def status_range(raw: str) -> tuple[int, int] | None:
    match = _STATUS_CLASS_RE.match(raw.strip())
    if match is None:
        return None
    base = int(match.group(1)) * 100
    return base, base + 99


def asn_number(raw: str, start: int, end: int) -> int:
    match = _ASN_RE.match(raw.strip())
    text = match.group(1) if match else raw.strip()
    if not text.isdigit():
        raise _fail(raw, "AS number", start, end)
    return int(_bounded(float(text), raw, start, end))


def moment(raw: str, start: int, end: int) -> datetime:
    text = raw.strip()
    now = utc_now()
    relative = _RELATIVE_RE.match(text)
    if relative is not None:
        seconds = float(relative.group(1)) * _RELATIVE[relative.group(2).lower()]
        return now - timedelta(seconds=seconds)
    if text.lower() in ("now", "today"):
        return now
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=now.tzinfo)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise _fail(raw, "date", start, end) from exc
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=now.tzinfo)


def network(raw: str) -> ipaddress.IPv4Network | ipaddress.IPv6Network | None:
    if "/" not in raw:
        return None
    try:
        return ipaddress.ip_network(raw.strip(), strict=False)
    except ValueError:
        return None


def split_range(raw: str) -> tuple[str, str] | None:
    if ".." not in raw:
        return None
    low, _, high = raw.partition("..")
    if not low.strip() or not high.strip():
        return None
    return low.strip(), high.strip()


def like(raw: str) -> str:
    escaped = raw.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def tsquery(raw: str, weight: str, prefix: bool = True) -> str:
    words = [w for w in re.split(r"[^\w./-]+", raw.lower()) if w]
    if not words:
        return ""
    star = "*" if prefix and len(words) == 1 else ""
    return " <-> ".join(f"'{w}':{star}{weight}" for w in words)


def is_relative(raw: str) -> bool:
    return _RELATIVE_RE.match(raw.strip()) is not None
