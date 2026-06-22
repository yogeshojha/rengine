from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from engines.subdomain.config import SubdomainConfig
    from engines.subdomain.providers.base import ProviderResult

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
    results: Iterable[ProviderResult], domain: str, cfg: SubdomainConfig
) -> dict[str, set[str]]:
    """Normalize, scope to the apex + included whitelist, merge per-source attribution.

    Excluded patterns are NOT dropped here — the engine stores them flagged is_excluded.
    """
    included = [normalize_host(x) or x.strip().lower() for x in cfg.included_subdomains]

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
