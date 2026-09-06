"""Uploaded typefaces. A face is stored bytes with a name we generate, never a path a user gives."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

FONT_ROOT = "/app/report-fonts"
MAX_FACE_BYTES = 2_000_000
MIN_FACE_BYTES = 1_024
MAX_FACES = 12
MAX_FAMILIES = 24
MAX_FAMILY_NAME = 80
FONT_SLUG_LENGTH = 48

WEIGHTS: tuple[int, ...] = (100, 200, 300, 400, 500, 600, 700, 800, 900)
DEFAULT_WEIGHT = 400


class FontRole(StrEnum):
    SANS = "sans"
    SERIF = "serif"
    MONO = "mono"


FONT_ROLES: tuple[str, ...] = tuple(r.value for r in FontRole)

FONT_ROLE_LABELS: dict[str, str] = {
    FontRole.SANS.value: "Sans",
    FontRole.SERIF.value: "Serif",
    FontRole.MONO.value: "Monospaced",
}

FONT_ROLE_HELP: dict[str, str] = {
    FontRole.SANS.value: "Offered for headings and body text.",
    FontRole.SERIF.value: "Offered for headings and body text.",
    FontRole.MONO.value: "Offered for code, evidence and labels.",
}


class FontOrigin(StrEnum):
    BUILTIN = "builtin"
    CUSTOM = "custom"


@dataclass(frozen=True)
class FontFormat:
    extension: str
    css_format: str
    media_type: str
    magic: tuple[bytes, ...]


# the signature is checked against the bytes, so a renamed file is refused
FONT_FORMATS: tuple[FontFormat, ...] = (
    FontFormat("woff2", "woff2", "font/woff2", (b"wOF2",)),
    FontFormat("woff", "woff", "font/woff", (b"wOFF",)),
    FontFormat("ttf", "truetype", "font/ttf", (b"\x00\x01\x00\x00", b"true", b"ttcf")),
    FontFormat("otf", "opentype", "font/otf", (b"OTTO",)),
)

FORMAT_BY_EXTENSION: dict[str, FontFormat] = {f.extension: f for f in FONT_FORMATS}
FONT_EXTENSIONS: tuple[str, ...] = tuple(f.extension for f in FONT_FORMATS)


def detect_format(data: bytes) -> FontFormat | None:
    """The format a file actually is, read from its own bytes."""
    for spec in FONT_FORMATS:
        if any(data.startswith(magic) for magic in spec.magic):
            return spec
    return None


# a family name is written into a quoted CSS string, so it may not carry string syntax
_UNSAFE_NAME = frozenset("'\"\\;{}<>()")
_CONTROL = 32


def clean_family_name(value: str) -> str:
    name = " ".join((value or "").split())
    if not name:
        msg = "Give the typeface a name."
        raise ValueError(msg)
    if any(ch in _UNSAFE_NAME or ord(ch) < _CONTROL for ch in name):
        msg = "A typeface name may not contain quotes, brackets, semicolons or control characters."
        raise ValueError(msg)
    if len(name) > MAX_FAMILY_NAME:
        msg = f"A typeface name must be under {MAX_FAMILY_NAME} characters."
        raise ValueError(msg)
    return name


def face_filename(slug: str, weight: int, *, italic: bool, extension: str) -> str:
    return f"{slug}-{weight}{'-italic' if italic else ''}.{extension}"
