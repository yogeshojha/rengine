"""sRGB ↔ OKLCH, so a theme names one colour and the document derives the rest."""

from __future__ import annotations

import math

_M1 = (
    (0.4122214708, 0.5363325363, 0.0514459929),
    (0.2119034982, 0.6806995451, 0.1073969566),
    (0.0883024619, 0.2817188376, 0.6299787005),
)
_M2 = (
    (0.2104542553, 0.7936177850, -0.0040720468),
    (1.9779984951, -2.4285922050, 0.4505937099),
    (0.0259040371, 0.7827717662, -0.8086757660),
)
_M2_INV = (
    (1.0, 0.3963377774, 0.2158037573),
    (1.0, -0.1055613458, -0.0638541728),
    (1.0, -0.0894841775, -1.2914855480),
)
_M1_INV = (
    (4.0767416621, -3.3077115913, 0.2309699292),
    (-1.2684380046, 2.6097574011, -0.3413193965),
    (-0.0041960863, -0.7034186147, 1.7076147010),
)


_LINEAR_CUT = 0.04045
_SRGB_CUT = 0.0031308
_SHORT_HEX = 3
_FULL_HEX = 6
_DARK_BELOW = 0.5


def _to_linear(value: float) -> float:
    return value / 12.92 if value <= _LINEAR_CUT else ((value + 0.055) / 1.055) ** 2.4


def _to_srgb(value: float) -> float:
    return value * 12.92 if value <= _SRGB_CUT else 1.055 * value ** (1 / 2.4) - 0.055


def parse_hex(value: str) -> tuple[float, float, float] | None:
    text = (value or "").strip().lstrip("#")
    if len(text) == _SHORT_HEX:
        text = "".join(c * 2 for c in text)
    if len(text) != _FULL_HEX:
        return None
    try:
        number = int(text, 16)
    except ValueError:
        return None
    return (
        (number >> 16 & 255) / 255,
        (number >> 8 & 255) / 255,
        (number & 255) / 255,
    )


def to_oklch(value: str) -> tuple[float, float, float] | None:
    rgb = parse_hex(value)
    if rgb is None:
        return None
    lin = [_to_linear(c) for c in rgb]
    lms = [sum(row[i] * lin[i] for i in range(3)) ** (1 / 3) for row in _M1]
    lab = [sum(row[i] * lms[i] for i in range(3)) for row in _M2]
    chroma = math.hypot(lab[1], lab[2])
    hue = math.degrees(math.atan2(lab[2], lab[1])) % 360
    return lab[0], chroma, hue


def from_oklch(lightness: float, chroma: float, hue: float) -> str:
    radians = math.radians(hue)
    lab = (lightness, chroma * math.cos(radians), chroma * math.sin(radians))
    lms = [sum(row[i] * lab[i] for i in range(3)) ** 3 for row in _M2_INV]
    lin = [sum(row[i] * lms[i] for i in range(3)) for row in _M1_INV]
    parts = [max(0, min(255, round(_to_srgb(c) * 255))) for c in lin]
    return "#{:02x}{:02x}{:02x}".format(*parts)


def restate(value: str, lightness: float, chroma: float, fallback: str = "") -> str:
    """The same hue at a stated lightness and chroma. Chroma is a fraction of the source's."""
    parsed = to_oklch(value)
    if parsed is None:
        return fallback or value
    _, source_chroma, hue = parsed
    return from_oklch(lightness, min(source_chroma * chroma, 0.37), hue)


def tint(value: str, lightness: float = 0.968) -> str:
    """A wash of the colour, for a badge or a callout ground."""
    return restate(value, lightness, 0.20, fallback=value)


def ink(value: str, lightness: float = 0.44) -> str:
    """The colour darkened until it can carry text on its own tint."""
    return restate(value, lightness, 0.85, fallback=value)


def mix(value: str, other: str, amount: float) -> str:
    """Blend two colours in linear light. `amount` is how much of `other`."""
    first, second = parse_hex(value), parse_hex(other)
    if first is None or second is None:
        return value
    blended = [
        _to_srgb(_to_linear(a) * (1 - amount) + _to_linear(b) * amount)
        for a, b in zip(first, second, strict=True)
    ]
    parts = [max(0, min(255, round(c * 255))) for c in blended]
    return "#{:02x}{:02x}{:02x}".format(*parts)


def is_dark(value: str) -> bool:
    parsed = to_oklch(value)
    return parsed is not None and parsed[0] < _DARK_BELOW
