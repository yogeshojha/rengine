from __future__ import annotations

import html
import re
from urllib.parse import urljoin

MAX_URL = 2000

ATTRIBUTE_RE = re.compile(
    r"""(?:href|src|action|data-url|data-href|data-src|formaction)\s*=\s*"""
    r"""["']([^"'<>\s]{1,2000})["']""",
    re.IGNORECASE,
)
ABSOLUTE_RE = re.compile(r"""https?://[^\s"'<>()\[\]{}\\`]{4,1500}""", re.IGNORECASE)
QUOTED_PATH_RE = re.compile(
    r"""["'`](/[A-Za-z0-9_\-./~%]{1,300}(?:\?[A-Za-z0-9_\-.=&%~+/]{0,200})?)["'`]"""
)
LINK_HEADER_RE = re.compile(r"<([^>]{1,1500})>")

MINED_HEADERS = ("link", "content-location", "location", "refresh")
SKIP_PREFIXES = ("javascript:", "mailto:", "tel:", "data:", "blob:", "about:", "#")
PLACEHOLDER = ("{{", "${", "%7b%7b", "<%", "[[")


def candidates(body: str, headers: dict | None = None) -> list[str]:
    out: list[str] = []
    out.extend(ATTRIBUTE_RE.findall(body))
    out.extend(ABSOLUTE_RE.findall(body))
    out.extend(QUOTED_PATH_RE.findall(body))
    for name, value in (headers or {}).items():
        if name.lower() not in MINED_HEADERS or not isinstance(value, str):
            continue
        out.extend(LINK_HEADER_RE.findall(value) or [value])
    return out


def resolve(base: str, candidate: str) -> str | None:
    """Absolute url, or None when the string is not one."""
    value = html.unescape(candidate.strip())
    if not value or len(value) > MAX_URL:
        return None
    lowered = value.lower()
    if lowered.startswith(SKIP_PREFIXES) or any(t in lowered for t in PLACEHOLDER):
        return None
    try:
        return urljoin(base, value)
    except ValueError:
        return None
