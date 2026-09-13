from __future__ import annotations

from typing import TYPE_CHECKING

from shared.utils.validation import normalize_host

if TYPE_CHECKING:
    from collections.abc import Iterable

    from stages.subdomain.providers.base import ProviderResult

__all__ = ["in_scope", "merge_and_filter", "normalize_host", "passes_included"]


def in_scope(name: str, domain: str) -> bool:
    return name == domain or name.endswith("." + domain)


def _matches_any(name: str, patterns: list[str]) -> bool:
    return any(name == p or name.endswith("." + p) for p in patterns if p)


def passes_included(name: str, included: list[str]) -> bool:
    return (not included) or _matches_any(name, included)


def merge_and_filter(
    results: Iterable[ProviderResult], domain: str, included_subdomains: list[str]
) -> dict[str, set[str]]:
    """Scope to apex + included, merge sources."""
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
