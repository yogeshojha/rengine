"""Generated names dropped before resolution."""

from __future__ import annotations

import re
from enum import StrEnum

from shared.enums.subdomain import SubdomainSource


class NameRule(StrEnum):
    REVERSE_DNS = "reverse_dns"


# sources that repeat third-party datasets
AGGREGATOR_SOURCES: frozenset[str] = frozenset(
    {
        SubdomainSource.SUBFINDER.value,
        SubdomainSource.ASSETFINDER.value,
        SubdomainSource.AMASS.value,
        SubdomainSource.NETLAS.value,
        SubdomainSource.GITHUB.value,
    }
)

_OCTET = r"(?:25[0-5]|2[0-4]\d|[01]?\d?\d)"
_ADDRESS = re.compile(rf"(?<!\d){_OCTET}[-_.]{_OCTET}[-_.]{_OCTET}[-_.]{_OCTET}(?!\d)")
_OCTET_LABEL = re.compile(rf"^{_OCTET}$")
# labels under the apex that spell a partial address
_MIN_OCTET_LABELS = 3


def reverse_dns_shaped(name: str, apex: str) -> bool:
    """A name whose labels under the apex spell an IPv4 address."""
    suffix = f".{apex}"
    if not name.endswith(suffix):
        return False
    head = name[: -len(suffix)]
    if _ADDRESS.search(head):
        return True
    labels = head.split(".")
    return len(labels) >= _MIN_OCTET_LABELS and all(
        _OCTET_LABEL.match(label) for label in labels
    )


def sift(
    merged: dict[str, set[str]], apex: str
) -> tuple[dict[str, set[str]], dict[str, str]]:
    """The names kept, and each dropped name with its rule."""
    kept: dict[str, set[str]] = {}
    dropped: dict[str, str] = {}
    for name, sources in merged.items():
        if sources <= AGGREGATOR_SOURCES and reverse_dns_shaped(name, apex):
            dropped[name] = NameRule.REVERSE_DNS.value
            continue
        kept[name] = sources
    return kept, dropped


__all__ = ["AGGREGATOR_SOURCES", "NameRule", "reverse_dns_shaped", "sift"]
