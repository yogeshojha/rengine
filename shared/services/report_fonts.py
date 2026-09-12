"""The only reader and writer of uploaded font files."""

from __future__ import annotations

import base64
import binascii
from pathlib import Path

from shared.definitions.report_fonts import (
    FONT_ROOT,
    MAX_FACE_BYTES,
    MIN_FACE_BYTES,
    FontOrigin,
    clean_family_name,
    detect_format,
    face_filename,
)
from shared.logging import get_logger
from shared.utils.slug import generate_slug

logger = get_logger(__name__)


class FontError(ValueError):
    """An uploaded face could not be stored."""


def root() -> Path:
    path = Path(FONT_ROOT)
    path.mkdir(parents=True, exist_ok=True)
    return path


def family_dir(slug: str) -> Path:
    """The family directory under the font root."""
    base = root()
    candidate = (base / slug).resolve()
    if not candidate.is_relative_to(base.resolve()):
        msg = "The family name is not allowed."
        raise FontError(msg)
    return candidate


def clean_name(name: str) -> str:
    try:
        return clean_family_name(name)
    except ValueError as exc:
        raise FontError(str(exc)) from exc


def slugify(name: str) -> str:
    slug = generate_slug(clean_name(name))[:48]
    if not slug:
        msg = "The family name must contain letters or digits."
        raise FontError(msg)
    return slug


def decode(content: str) -> bytes:
    payload = content.split(",", 1)[-1] if content.startswith("data:") else content
    try:
        data = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        msg = "The file could not be decoded."
        raise FontError(msg) from exc
    if not data:
        msg = "The file is empty."
        raise FontError(msg)
    if len(data) > MAX_FACE_BYTES:
        msg = f"A face must be under {MAX_FACE_BYTES // 1024} KB."
        raise FontError(msg)
    if len(data) < MIN_FACE_BYTES:
        msg = "The file is too small to be a typeface."
        raise FontError(msg)
    return data


def store_face(slug: str, data: bytes, *, weight: int, italic: bool) -> dict:
    """Write one face."""
    spec = detect_format(data)
    if spec is None:
        msg = "The file is not a WOFF2, WOFF, TrueType or OpenType font."
        raise FontError(msg)
    _parse_or_reject(data)
    directory = family_dir(slug)
    directory.mkdir(parents=True, exist_ok=True)
    name = face_filename(slug, weight, italic=italic, extension=spec.extension)
    (directory / name).write_bytes(data)
    return {
        "weight": weight,
        "italic": italic,
        "filename": name,
        "format": spec.css_format,
        "bytes": len(data),
    }


def _parse_or_reject(data: bytes) -> None:
    """Parse the font or reject it."""
    import io  # noqa: PLC0415

    try:
        from fontTools.ttLib import TTFont  # noqa: PLC0415

        font = TTFont(io.BytesIO(data), lazy=True, fontNumber=0)
        if "glyf" not in font and "CFF " not in font and "CFF2" not in font:
            msg = "The font has no outlines."
            raise FontError(msg)
    except FontError:
        raise
    except Exception as exc:
        logger.info("font rejected", error=str(exc)[:160])
        msg = "The file could not be opened as a typeface."
        raise FontError(msg) from exc


def face_path(slug: str, filename: str) -> Path | None:
    """Resolve a stored face inside its family directory."""
    directory = family_dir(slug)
    candidate = (directory / filename).resolve()
    if not candidate.is_relative_to(directory) or not candidate.is_file():
        return None
    return candidate


def delete_family(slug: str, origin: str) -> None:
    if origin != FontOrigin.CUSTOM.value:
        msg = "A shipped typeface cannot be deleted."
        raise FontError(msg)
    directory = family_dir(slug)
    if not directory.is_dir():
        return
    for item in directory.iterdir():
        if item.is_file():
            item.unlink(missing_ok=True)
    directory.rmdir()
