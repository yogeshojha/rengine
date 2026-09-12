"""Software identity: the version a banner states, and a key postgres can range-compare."""

from __future__ import annotations

import re

MAX_NAME = 120
MAX_VERSION = 64
MAX_CPE = 300
MAX_COMPONENTS = 60
BANNER_STATED = "banner"
BANNER_FINGERPRINT = "fingerprint"
_SEGMENTS = 16
_PAD = 8
_ZERO = "0" * 8
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


def version_key(version: str | None) -> str | None:
    """Zero-padded so a string comparison in SQL orders versions correctly."""
    if not version:
        return None
    parts: list[str] = []
    for token in _SPLIT.split(version.strip()):
        for run in _RUNS.findall(token):
            if run.isdigit():
                parts.append(run[-_PAD:].zfill(_PAD))
            else:
                parts.append(f"{_ALPHA_PREFIX}{run.lower()[:_PAD]}")
            if len(parts) >= _SEGMENTS:
                return ".".join(parts)
    while len(parts) > 1 and parts[-1] == _ZERO:
        parts.pop()
    return ".".join(parts) or None


def version_kind(key: str | None) -> str | None:
    """Numeric and alphabetic version schemes are never ordered against each other."""
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
    """A Server header states product, version and often the distribution that built it."""
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


def cpe23(vendor: str, product: str, version: str | None) -> str:
    """A CPE 2.3 string with the version filled in, escaped as the dictionary escapes it."""
    field = _cpe_escape(version) if version else "*"
    return (
        f"cpe:2.3:a:{_cpe_escape(vendor)}:{_cpe_escape(product)}:{field}:*:*:*:*:*:*:*"[
            :MAX_CPE
        ]
    )


def _cpe_escape(value: str) -> str:
    return re.sub(r"([:\\*?!\"#$%&'()+,/;<=>@\[\]^`{|}~])", r"\\\1", value)


def components_of(tech: list[str], webserver: str | None) -> list[dict]:
    """A technology that names its version is the only one a CVE lookup can use."""
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []
    for entry in tech:
        name, version = parse_tech(str(entry))
        if not version or (name, version) in seen:
            continue
        seen.add((name, version))
        out.append({"name": name, "version": version, "source": BANNER_FINGERPRINT})
        if len(out) >= MAX_COMPONENTS:
            return out
    product, version, distro = parse_banner(webserver)
    if product and version and (product, version) not in seen:
        out.append(
            {
                "name": product,
                "version": version,
                "source": BANNER_STATED,
                "distro": distro,
            }
        )
    return out
