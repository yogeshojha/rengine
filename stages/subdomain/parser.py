from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from stages.subdomain.providers.base import ProviderResult

_HOST_RE = re.compile(
    r"^(?=.{1,253}$)([a-z0-9_](?:[a-z0-9_-]{0,62}[a-z0-9_])?\.)+[a-z0-9][a-z0-9-]{0,62}$"
)


def normalize_host(raw: str) -> str | None:
    if not raw:
        return None
    name = raw.strip().lower().rstrip(".")
    if name.startswith("*."):
        name = name[2:]
    if not name or "." not in name or " " in name or "/" in name or "@" in name:
        return None
    if not _HOST_RE.match(name):
        return None
    return name


def in_scope(name: str, domain: str) -> bool:
    return name == domain or name.endswith("." + domain)


def _matches_any(name: str, patterns: list[str]) -> bool:
    return any(name == p or name.endswith("." + p) for p in patterns if p)


def passes_included(name: str, included: list[str]) -> bool:
    return (not included) or _matches_any(name, included)


def merge_and_filter(
    results: Iterable[ProviderResult], domain: str, included_subdomains: list[str]
) -> dict[str, set[str]]:
    """Scope to apex + included, merge sources; excluded names are kept for the caller to flag."""
    included = [normalize_host(x) or x.strip().lower() for x in included_subdomains]

    merged: dict[str, set[str]] = {}
    for result in results:
        for raw in result.subdomains:
            name = normalize_host(raw)
            if not name or not in_scope(name, domain):
                continue
            if not passes_included(name, included):
                continue
            merged.setdefault(name, set()).add(result.source.value)
    return merged
