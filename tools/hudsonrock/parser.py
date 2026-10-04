from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import unquote, urlsplit

from shared.definitions.infostealer import (
    MAX_APPLICATIONS,
    MAX_FAMILIES,
    MAX_HOST_LENGTH,
    MAX_LOGINS,
    MAX_NAME_LENGTH,
    MAX_PATH_LENGTH,
    MAX_THIRD_PARTIES,
    STRENGTH_ORDER,
    Audience,
)
from shared.utils.text import strip_control
from shared.utils.validation import normalize_host
from tools.hudsonrock.models import InfostealerReport, LoginUrl, NamedCount

_SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.-]*://", re.IGNORECASE)
_SLASHES_RE = re.compile(r"/{2,}")
_WEB_SCHEMES = frozenset({"http", "https"})
_DEFAULT_PORTS = {"http": 80, "https": 443, "ftp": 21}
# IBM WebSphere Portal state
_PORTAL_STATE = "/!ut/"

_URL_LISTS: tuple[tuple[str, str], ...] = (
    ("employees_urls", Audience.EMPLOYEE.value),
    ("clients_urls", Audience.USER.value),
)
_PASSWORD_BLOCKS: tuple[tuple[str, str], ...] = (
    ("employeePasswords", Audience.EMPLOYEE.value),
    ("userPasswords", Audience.USER.value),
)
_AUDIENCE_RANK = {Audience.EMPLOYEE.value: 0, Audience.USER.value: 1}


def _count(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return 0
    return max(0, int(value))


def _when(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (
        parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
    )


def _name(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = strip_control(value).strip()
    return text if text and len(text) <= MAX_NAME_LENGTH else None


def _path(raw: str) -> str | None:
    cut = raw.find(_PORTAL_STATE)
    path = raw[:cut] if cut >= 0 else raw
    path = "/".join(segment.split(";", 1)[0] for segment in path.split("/"))
    path = strip_control(unquote(_SLASHES_RE.sub("/", path or "/"), errors="replace"))
    path = path.rstrip("/") or "/"
    if not path.startswith("/"):
        path = f"/{path}"
    return path if len(path) <= MAX_PATH_LENGTH else None


def clean_login(
    raw: object, domain: str
) -> tuple[str, str | None, int | None, str | None] | None:
    """Host, scheme, port and path of a login URL under the domain."""
    if not isinstance(raw, str):
        return None
    text = strip_control(raw).strip()
    if not text:
        return None
    try:
        parts = urlsplit(text if _SCHEME_RE.match(text) else f"//{text}")
        port = parts.port
    except ValueError:
        return None
    host = normalize_host(parts.hostname or "")
    if host is None or len(host) > MAX_HOST_LENGTH:
        return None
    if host != domain and not host.endswith(f".{domain}"):
        return None
    scheme = parts.scheme.lower() or None
    if port is not None and port == _DEFAULT_PORTS.get(scheme or "", 0):
        port = None
    if port in (80, 443) and scheme is None:
        port = None
    return host, None if scheme in _WEB_SCHEMES else scheme, port, _path(parts.path)


def _logins(data: object, domain: str) -> list[LoginUrl]:
    if not isinstance(data, dict):
        return []
    grouped: dict[tuple, list] = {}
    for key, audience in _URL_LISTS:
        rows = data.get(key)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            cleaned = clean_login(row.get("url"), domain)
            if cleaned is None:
                continue
            host, scheme, port, path = cleaned
            credentials = _count(row.get("occurrence"))
            group = (audience, host, scheme, port, path.casefold() if path else None)
            entry = grouped.setdefault(group, [0, path, -1])
            entry[0] += credentials
            if credentials > entry[2]:
                entry[1], entry[2] = path, credentials
    logins = [
        LoginUrl(
            audience=audience,
            host=host,
            scheme=scheme,
            port=port,
            path=spelling,
            credentials=total,
        )
        for (audience, host, scheme, port, _), (total, spelling, _) in grouped.items()
    ]
    logins.sort(
        key=lambda login: (
            _AUDIENCE_RANK[login.audience],
            -login.credentials,
            login.host,
            login.path or "",
        )
    )
    return logins[:MAX_LOGINS]


def _families(blob: object) -> list[NamedCount]:
    if not isinstance(blob, dict):
        return []
    rows = [
        NamedCount(name=name, count=_count(count))
        for raw, count in blob.items()
        if raw != "total" and (name := _name(raw)) and _count(count) > 0
    ]
    rows.sort(key=lambda r: (-(r.count or 0), r.name))
    return rows[:MAX_FAMILIES]


def _passwords(payload: dict) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for key, audience in _PASSWORD_BLOCKS:
        block = payload.get(key)
        if not isinstance(block, dict) or _count(block.get("totalPass")) == 0:
            continue
        buckets: dict[str, int] = {}
        for strength in STRENGTH_ORDER:
            bucket = block.get(strength)
            buckets[strength] = (
                _count(bucket.get("qty")) if isinstance(bucket, dict) else 0
            )
        if sum(buckets.values()):
            out[audience] = buckets
    return out


def _named(rows: object, name_key: str, count_key: str, limit: int) -> list[NamedCount]:
    if not isinstance(rows, list):
        return []
    out: list[NamedCount] = []
    for row in rows:
        if not isinstance(row, dict) or not (name := _name(row.get(name_key))):
            continue
        count = row.get(count_key)
        out.append(
            NamedCount(name=name, count=_count(count) if count is not None else None)
        )
    out.sort(key=lambda r: (-(r.count or 0), r.name))
    return out[:limit]


def parse_domain_report(payload: Any, domain: str) -> InfostealerReport | None:
    """None when the answer is not a domain report."""
    if not isinstance(payload, dict) or "total" not in payload:
        return None
    return InfostealerReport(
        domain=domain,
        total=_count(payload.get("total")),
        employees=_count(payload.get("employees")),
        users=_count(payload.get("users")),
        third_parties=_count(payload.get("third_parties")),
        total_urls=_count(payload.get("totalUrls")),
        last_employee_at=_when(payload.get("last_employee_compromised")),
        last_user_at=_when(payload.get("last_user_compromised")),
        logins=_logins(payload.get("data"), domain),
        families=_families(payload.get("stealerFamilies")),
        passwords=_passwords(payload),
        applications=_named(
            payload.get("applications"), "keyword", "count", MAX_APPLICATIONS
        ),
        services=_named(
            payload.get("thirdPartyDomains"), "domain", "occurrence", MAX_THIRD_PARTIES
        ),
    )
