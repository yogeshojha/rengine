"""Path shaping: /api/users/1234 and /api/users/9999 resolve to one shape."""

from __future__ import annotations

import re

PLACEHOLDER = "{id}"
_MIN_TOKEN = 12

_NUMERIC = re.compile(r"^\d+$")
_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)
_HEX = re.compile(r"^[0-9a-f]{16,}$", re.IGNORECASE)
_TOKEN = re.compile(r"^[A-Za-z0-9_-]{20,}$")
_MIXED = re.compile(r"^(?=.*\d)(?=.*[A-Za-z])[A-Za-z0-9]{8,}$")
_HAS_DOT = re.compile(r"\.")

_MIN_STEM = 10
_MIN_DIGITS = 3
_HASH_STEM = re.compile(r"^[a-z0-9]+$", re.IGNORECASE)
_NAMED_HASH = re.compile(r"^(.+)-([a-z0-9]{8,})$", re.IGNORECASE)


def _variable(segment: str) -> bool:
    if not segment or _HAS_DOT.search(segment):
        return False
    if _NUMERIC.match(segment) or _UUID.match(segment) or _HEX.match(segment):
        return True
    return bool(
        len(segment) >= _MIN_TOKEN and (_TOKEN.match(segment) or _MIXED.match(segment))
    )


def _hashed_filename(segment: str) -> str | None:
    """A build-hashed filename collapsed to its stable part, or None when it reads as a name."""
    stem, dot, extension = segment.rpartition(".")
    if not dot or "." in stem:
        return None
    named = _NAMED_HASH.match(stem)
    if named and sum(c.isdigit() for c in named.group(2)) >= _MIN_DIGITS:
        return f"{named.group(1)}-{PLACEHOLDER}.{extension}"
    if (
        len(stem) >= _MIN_STEM
        and _HASH_STEM.match(stem)
        and sum(c.isdigit() for c in stem) >= _MIN_DIGITS
        and any(c.isalpha() for c in stem)
    ):
        return f"{PLACEHOLDER}.{extension}"
    return None


def templatize(path: str) -> tuple[str, int]:
    """Collapse identifier-looking segments into a single placeholder."""
    if not path or path == "/":
        return path or "/", 0
    trailing = path.endswith("/")
    parts = [p for p in path.split("/") if p]
    replaced = 0
    out: list[str] = []
    last = len(parts) - 1
    for index, segment in enumerate(parts):
        if _variable(segment):
            replaced += 1
            out.append(PLACEHOLDER)
            continue
        hashed = _hashed_filename(segment) if index == last else None
        if hashed is not None:
            replaced += 1
            out.append(hashed)
            continue
        out.append(segment)
    shaped = "/" + "/".join(out)
    if trailing and not shaped.endswith("/"):
        shaped += "/"
    return shaped, replaced
