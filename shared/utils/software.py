"""Software identity: the version a banner states, and a key postgres can range-compare."""

from __future__ import annotations

import re

from shared.definitions.software import MAX_COMPONENTS_PER_ASSET, VersionSource

MAX_NAME = 120
MAX_VERSION = 64
MAX_CPE = 300
_SEGMENTS = 16
_PAD = 8
_ZERO = "0" * _PAD
_ALPHA_PREFIX = "~"
KIND_NUMERIC = "n"
KIND_ALPHA = "a"

_SPLIT = re.compile(r"[._\-+:~ ]+")
_VERSION_HEAD = re.compile(r"^[vV]?(\d[\w.+\-]*)$")
_BANNER = re.compile(r"^([^/\s]+)(?:/(\S+))?")
_PAREN = re.compile(r"\(([^)]*)\)")
_UNESCAPE = re.compile(r"\\(.)")
_RUNS = re.compile(r"\d+|[^\d]+")
_TRAILING_JUNK = re.compile(r"[^\w.+\-]+$")

DISTRO_MARKERS: frozenset[str] = frozenset(
    {
        "ubuntu",
        "debian",
        "centos",
        "red hat",
        "redhat",
        "rhel",
        "fedora",
        "suse",
        "alpine",
        "amazon",
        "oracle",
        "rocky",
        "almalinux",
    }
)


def _numeric_segment(run: str) -> str:
    """A numeric run zero-padded to the pad width, clamped above it."""
    trimmed = run.lstrip("0") or "0"
    return trimmed.zfill(_PAD) if len(trimmed) <= _PAD else "9" * _PAD


def version_key(version: str | None) -> str | None:
    """A version key that orders releases under string comparison."""
    if not version:
        return None
    parts: list[str] = []
    for token in _SPLIT.split(version.strip()):
        for run in _RUNS.findall(token):
            if run.isdigit():
                parts.append(_numeric_segment(run))
            else:
                parts.append(f"{_ALPHA_PREFIX}{run.lower()[:_PAD]}")
            if len(parts) >= _SEGMENTS:
                return ".".join(parts)
    while len(parts) > 1 and parts[-1] == _ZERO:
        parts.pop()
    return ".".join(parts) or None


def version_kind(key: str | None) -> str | None:
    """The scheme of a version key, numeric or alphabetic."""
    if not key:
        return None
    return KIND_ALPHA if key.startswith(_ALPHA_PREFIX) else KIND_NUMERIC


def clean_version(raw: str | None) -> str | None:
    """A version a tool stated, or None when what it stated is not one."""
    if not raw:
        return None
    value = _TRAILING_JUNK.sub("", raw.strip())[:MAX_VERSION]
    match = _VERSION_HEAD.match(value)
    return match.group(1) if match else None


def parse_tech(entry: str) -> tuple[str, str | None]:
    """httpx writes a technology as Name or Name:version."""
    name, _, tail = entry.strip().rpartition(":")
    if not name:
        return entry.strip()[:MAX_NAME], None
    version = clean_version(tail)
    if version is None:
        return entry.strip()[:MAX_NAME], None
    return name.strip()[:MAX_NAME], version


def parse_banner(banner: str | None) -> tuple[str | None, str | None, str | None]:
    """Product, version and distribution from a Server header."""
    if not banner:
        return None, None, None
    head = _BANNER.match(banner.strip())
    if head is None:
        return None, None, None
    product = head.group(1)[:MAX_NAME] or None
    version = clean_version(head.group(2))
    distro = None
    for note in _PAREN.findall(banner):
        marker = note.strip().lower()
        if marker in DISTRO_MARKERS:
            distro = marker
            break
    return product, version, distro


def normalize_product(name: str) -> str:
    """The shape NVD writes a product in: lower case, words joined, dots kept."""
    lowered = _UNESCAPE.sub(r"\1", name.strip().lower())
    collapsed = re.sub(r"[^a-z0-9.]+", "_", lowered)
    return collapsed.strip("_")


def components_of(tech: list[str], webserver: str | None) -> list[dict]:
    """The versioned components of an asset's technologies and Server header."""
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []
    for entry in tech:
        name, version = parse_tech(str(entry))
        if not version or (name, version) in seen:
            continue
        seen.add((name, version))
        out.append(
            {
                "name": name,
                "version": version,
                "source": VersionSource.FINGERPRINT.value,
            }
        )
        if len(out) >= MAX_COMPONENTS_PER_ASSET:
            return out
    product, version, distro = parse_banner(webserver)
    if product and version and (product, version) not in seen:
        out.append(
            {
                "name": product,
                "version": version,
                "source": VersionSource.BANNER.value,
                "distro": distro,
            }
        )
    return out
