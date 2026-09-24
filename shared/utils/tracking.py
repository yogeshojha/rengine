"""Analytics, tag manager and ads account IDs a page loads."""

from __future__ import annotations

import re

MAX_TRACKING_IDS = 20
BODY_SCAN_BYTES = 131_072

_QUOTED = r"""(?<=[\"'=/])"""
_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(_QUOTED + r"UA-(\d{4,10})-\d{1,4}(?![\w-])"), "UA-{}"),
    (re.compile(_QUOTED + r"(G-[A-Z0-9]{8,12})(?![\w-])"), "{}"),
    (re.compile(_QUOTED + r"(GTM-[A-Z0-9]{4,9})(?![\w-])"), "{}"),
    (re.compile(_QUOTED + r"(AW-\d{8,12})(?![\w-])"), "{}"),
    (re.compile(r"(ca-pub-\d{10,20})(?!\d)"), "{}"),
    (re.compile(r"""fbq\(\s*['"]init['"]\s*,\s*['"](\d{10,20})['"]"""), "fb:{}"),
    (re.compile(r"hjid\s*:\s*(\d{5,10})"), "hotjar:{}"),
    (re.compile(r"clarity\.ms/tag/([a-z0-9]{8,12})", re.IGNORECASE), "clarity:{}"),
    (re.compile(r"\bym\(\s*(\d{5,10})\s*,"), "ym:{}"),
    (re.compile(r"js\.hs-scripts\.com/(\d{5,10})\.js"), "hubspot:{}"),
)


def tracking_ids(body: str | None) -> list[str]:
    """Every account a page names, a Universal Analytics property folded to its account."""
    if not body:
        return []
    text = body[:BODY_SCAN_BYTES]
    found: dict[str, None] = {}
    for pattern, shape in _PATTERNS:
        for match in pattern.findall(text):
            found.setdefault(shape.format(match), None)
            if len(found) >= MAX_TRACKING_IDS:
                return sorted(found)
    return sorted(found)
