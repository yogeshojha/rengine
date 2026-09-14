"""What a web asset was seen running, as the tags the check library uses."""

from __future__ import annotations

from collections.abc import Iterable

from shared.definitions.scan_surface import (
    TECH_IGNORED,
    normalize_tech,
    tags_for_tech,
)

_CPE_PARTS = 5


def _cpe_product(cpe: str) -> str | None:
    parts = (cpe or "").split(":")
    if len(parts) < _CPE_PARTS or parts[0] != "cpe":
        return None
    if parts[1] == "2.3":
        return parts[4] or None
    return parts[3] or None


def _software_names(software: Iterable) -> list[str]:
    names: list[str] = []
    for entry in software or ():
        if isinstance(entry, dict):
            name = entry.get("name") or entry.get("product")
        else:
            name = entry
        if isinstance(name, str) and name.strip():
            names.append(name)
    return names


def host_tags(
    *,
    tech: Iterable[str],
    cpe: Iterable[str],
    webserver: str | None,
    software: Iterable,
    vocabulary: frozenset[str],
) -> tuple[list[str], list[str]]:
    """Tags the library carries for this software, and the names that map to none."""
    found: set[str] = set()
    unmapped: list[str] = []
    seen: set[str] = set()

    names: list[str] = [*tech, *_software_names(software)]
    if webserver:
        names.append(webserver)
    for name in names:
        key = normalize_tech(name)
        if not key or key in seen:
            continue
        seen.add(key)
        mapped = tags_for_tech(name)
        if mapped is None:
            compact = key.replace(" ", "")
            if compact in vocabulary:
                found.add(compact)
            elif key in vocabulary:
                found.add(key)
            elif key not in TECH_IGNORED:
                unmapped.append(name.split(":", 1)[0].strip())
            continue
        found.update(t for t in mapped if t in vocabulary)

    for entry in cpe:
        product = _cpe_product(str(entry))
        if not product:
            continue
        token = normalize_tech(product.replace("_", " ")).replace(" ", "")
        if token in vocabulary:
            found.add(token)
    return sorted(found), sorted(set(unmapped))


__all__ = ["host_tags"]
