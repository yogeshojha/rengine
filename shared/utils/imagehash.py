"""The perceptual hash of a rendered page."""

from __future__ import annotations

from collections.abc import Iterable
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


def _bands(radius: int) -> tuple[tuple[int, int], ...]:
    count = radius + 1
    width, extra = divmod(64, count)
    out, start = [], 0
    for i in range(count):
        size = width + (1 if i < extra else 0)
        out.append((start, (1 << size) - 1))
        start += size
    return tuple(out)


class NearIndex:
    """Hashes within `radius` bits of a query, found through exact-match bands."""

    def __init__(self, values: Iterable[int], radius: int):
        self.radius = radius
        self.bands = _bands(radius)
        self.buckets: list[dict[int, list[int]]] = [{} for _ in self.bands]
        for value in values:
            raw = to_unsigned(value)
            for (shift, mask), bucket in zip(self.bands, self.buckets, strict=True):
                bucket.setdefault((raw >> shift) & mask, []).append(value)

    def near(self, value: int) -> set[int]:
        raw = to_unsigned(value)
        found: set[int] = set()
        for (shift, mask), bucket in zip(self.bands, self.buckets, strict=True):
            for other in bucket.get((raw >> shift) & mask, ()):
                if other not in found and distance(value, other) <= self.radius:
                    found.add(other)
        return found


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
