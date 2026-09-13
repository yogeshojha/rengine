"""The perceptual hash of a rendered page."""

from __future__ import annotations

from pathlib import Path

HASH_SIZE = 8
DIGEST_CHARS = 16
# the viewport band a full-page render is cut back to, as a fraction of its width
VIEWPORT_ASPECT = 0.625
_SIGN_BIT = 1 << 63
_WRAP = 1 << 64
_ROW = HASH_SIZE + 1


def to_signed(value: int) -> int:
    """A 64-bit hash as the bigint Postgres stores."""
    return value - _WRAP if value >= _SIGN_BIT else value


def to_unsigned(value: int) -> int:
    return value + _WRAP if value < 0 else value


def hex_digest(value: int) -> str:
    return f"{to_unsigned(value):016x}"


def popcount(value: int) -> int:
    return to_unsigned(value).bit_count()


def distance(left: int, right: int) -> int:
    return (to_unsigned(left) ^ to_unsigned(right)).bit_count()


def phash_image(img) -> int:
    """The dHash of an already decoded render."""
    from PIL import Image  # noqa: PLC0415

    width, height = img.size
    band = min(height, max(1, round(width * VIEWPORT_ASPECT)))
    grey = img.convert("L").crop((0, 0, width, band))
    pixels = grey.resize((_ROW, HASH_SIZE), Image.Resampling.BOX).tobytes()
    bits = 0
    for y in range(HASH_SIZE):
        base = y * _ROW
        for x in range(HASH_SIZE):
            bits = (bits << 1) | (pixels[base + x] > pixels[base + x + 1])
    return to_signed(bits)


def phash_file(path: str | Path) -> int | None:
    """The dHash of a rendered page, or None when the file is not a readable image."""
    from PIL import Image, UnidentifiedImageError  # noqa: PLC0415

    try:
        if Path(path).stat().st_size == 0:
            return None
        with Image.open(path) as img:
            return phash_image(img)
    except (OSError, UnidentifiedImageError, ValueError):
        return None
