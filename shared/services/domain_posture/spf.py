"""SPF parsing and the lookup count receivers apply."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

from shared.definitions.domain_posture import (
    SPF_INCLUDE_CAP,
    SPF_INCLUDE_DEPTH,
    SpfAll,
)

_SPF_PREFIX = "v=spf1"
_LOOKUP_MECHANISMS = ("include", "a", "mx", "ptr", "exists")
_ALL_RE = re.compile(r"(?:^|\s)([+\-~?]?)all(?:\s|$)", re.IGNORECASE)
_QUALIFIERS = {
    "": SpfAll.PASS,
    "+": SpfAll.PASS,
    "-": SpfAll.FAIL,
    "~": SpfAll.SOFTFAIL,
    "?": SpfAll.NEUTRAL,
}


def is_spf(value: str) -> bool:
    return value.strip().lower().startswith(_SPF_PREFIX)


def spf_records(txt: list[str]) -> list[str]:
    return [v.strip() for v in txt if is_spf(v)]


def all_qualifier(record: str) -> str:
    match = _ALL_RE.search(record)
    if not match:
        return SpfAll.ABSENT.value
    return _QUALIFIERS.get(match.group(1), SpfAll.PASS).value


def _terms(record: str) -> list[str]:
    return [t for t in record.split()[1:] if t]


def referenced_zones(record: str) -> set[str]:
    """Zones an include or redirect makes receivers look up."""
    out: set[str] = set()
    for term in _terms(record):
        name, value = _mechanism(term)
        if name in ("include", "redirect") and value:
            out.add(value.strip().rstrip(".").lower())
    return out


def redirect_target(record: str) -> str | None:
    """The zone a redirect= modifier delegates to."""
    for term in _terms(record):
        name, value = _mechanism(term)
        if name == "redirect" and value:
            return value.strip().rstrip(".").lower()
    return None


def _mechanism(term: str) -> tuple[str, str | None]:
    body = term.lstrip("+-~?")
    if ":" in body:
        name, _, value = body.partition(":")
        return name.split("/", 1)[0].lower(), value
    if "=" in body:
        name, _, value = body.partition("=")
        return name.lower(), value
    return body.split("/", 1)[0].lower(), None


@dataclass
class LookupCount:
    lookups: int = 0
    capped: bool = False
    visited: set[str] = field(default_factory=set)


def lookup_count(
    zone: str,
    record: str,
    resolve_txt: Callable[[str], list[str] | None],
) -> LookupCount:
    """DNS lookups the record costs, following include and redirect."""
    state = LookupCount()
    _walk(zone, record, resolve_txt, state, 0)
    return state


def _walk(
    zone: str,
    record: str,
    resolve_txt: Callable[[str], list[str] | None],
    state: LookupCount,
    depth: int,
) -> None:
    state.visited.add(zone.lower())
    for term in _terms(record):
        name, value = _mechanism(term)
        if name in _LOOKUP_MECHANISMS:
            state.lookups += 1
        if name not in ("include", "redirect") or not value:
            continue
        if name == "redirect":
            state.lookups += 1
        target = value.strip().rstrip(".").lower()
        if target in state.visited:
            continue
        if depth >= SPF_INCLUDE_DEPTH or len(state.visited) >= SPF_INCLUDE_CAP:
            state.capped = True
            continue
        txt = resolve_txt(target)
        if txt is None:
            state.capped = True
            continue
        nested = spf_records(txt)
        if nested:
            _walk(target, nested[0], resolve_txt, state, depth + 1)
