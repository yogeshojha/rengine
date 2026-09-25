"""Hostnames under the target referenced in a scan's stored responses."""

from __future__ import annotations

import re
from collections import defaultdict
from urllib.parse import urlsplit
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from shared.enums.subdomain import SubdomainSource
from shared.models.http_asset import HttpAsset

BODY_SCAN_BYTES = 500_000
_MAX_NAME = 253
_ESCAPES = (
    ("%2f", "/"),
    ("%2F", "/"),
    ("%3a", ":"),
    ("%3A", ":"),
    ("%40", "@"),
    ("\\/", "/"),
    ("\\u002f", "/"),
    ("\\u002F", "/"),
    ("\\x2f", "/"),
)


def _pattern(root: str) -> re.Pattern[str]:
    escaped = re.escape(root.lower())
    return re.compile(
        rf"(?<![a-z0-9.-])((?:[a-z0-9](?:[a-z0-9-]{{0,61}}[a-z0-9])?\.)+{escaped})"
        r"(?![a-z0-9-]|\.[a-z0-9])",
        re.IGNORECASE,
    )


def _unescape(text: str) -> str:
    for token, char in _ESCAPES:
        text = text.replace(token, char)
    return text


def _clean(name: str | None, root: str) -> str:
    host = (name or "").strip().lower().rstrip(".").removeprefix("*.")
    if not host or len(host) > _MAX_NAME or "*" in host:
        return ""
    return host if host == root or host.endswith(f".{root}") else ""


def _url_host(url: str | None) -> str:
    if not url:
        return ""
    try:
        return urlsplit(url).hostname or ""
    except ValueError:
        return ""


def harvest(
    rows: list[
        tuple[str | None, list | None, str | None, str | None, str | None, str | None]
    ],
    root: str,
) -> dict[str, set[str]]:
    """Hostnames under the root in each response, with the source of each."""
    root = root.lower().rstrip(".")
    pattern = _pattern(root)
    found: dict[str, set[str]] = defaultdict(set)

    def _add(name: str | None, source: SubdomainSource) -> None:
        host = _clean(name, root)
        if host:
            found[host].add(source.value)

    for subject, sans, header, location, final_url, body in rows:
        for name in (subject, *(sans or [])):
            _add(str(name) if name else None, SubdomainSource.TLS_CERT)
        for url in (location, final_url):
            _add(_url_host(url), SubdomainSource.REDIRECT)
        if header:
            for match in pattern.findall(_unescape(header)):
                _add(match, SubdomainSource.RESPONSE_HEADER)
        if body:
            for match in pattern.findall(_unescape(body)):
                _add(match, SubdomainSource.PAGE_LINK)
    return dict(found)


def mentioned(
    session: Session, scan_id: UUID, root: str, hosts: set[str] | None = None
) -> dict[str, set[str]]:
    """Hostnames referenced in a scan's stored responses, or in those of the given hosts."""
    query = select(
        HttpAsset.tls_subject_cn,
        HttpAsset.tls_sans,
        HttpAsset.raw_response_header,
        HttpAsset.location,
        HttpAsset.final_url,
        func.left(HttpAsset.response_body, BODY_SCAN_BYTES),
    ).where(HttpAsset.scan_id == scan_id)
    if hosts is not None:
        if not hosts:
            return {}
        query = query.where(HttpAsset.host.in_(sorted(hosts)))
    rows = [tuple(r) for r in session.execute(query).all()]
    return harvest(rows, root)
