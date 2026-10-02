from __future__ import annotations

import math
from dataclasses import dataclass
from html import escape

from shared.utils.text import clip

_TAU = math.pi * 2
_MIN_SLICES = 2
_MIN_POINTS = 2
_ARC_EPSILON = 0.005
_THOUSAND = 1000
_STACK_WIDTH = 480
_STACK_GAP = 1.5
_BAR_ROW = 17
_BAR_VALUE_WIDTH = 44
_DIAL_SIZE = 120
_DIAL_THICKNESS = 8

DEFAULT_PALETTE: dict[str, str] = {
    "ink": "#16181d",
    "ink_soft": "#4a4f5a",
    "ink_faint": "#82889a",
    "surface": "#eef0f3",
    "accent": "#4f46e5",
    "accent_ink": "#ffffff",
    "rule": "#d8dbe2",
}


def _p(palette: dict[str, str] | None) -> dict[str, str]:
    return {
        key: _attr(value)
        for key, value in {**DEFAULT_PALETTE, **(palette or {})}.items()
    }


def _attr(value: str) -> str:
    return escape(str(value), quote=True)


@dataclass(frozen=True)
class Slice:
    label: str
    value: float
    fill: str = "#4f46e5"
    note: str = ""


def _fmt(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _open(width: float, height: float, extra: str = "") -> str:
    return (
        f'<svg viewBox="0 0 {_fmt(width)} {_fmt(height)}" '
        f'preserveAspectRatio="xMidYMid meet" role="img" {extra}>'
    )


def donut(
    slices: list[Slice],
    *,
    size: float = 120,
    thickness: float = 20,
    centre_value: str = "",
    centre_label: str = "",
    palette: dict[str, str] | None = None,
) -> str:
    """A ring."""
    live = [s for s in slices if s.value > 0]
    total = sum(s.value for s in live)
    if len(live) < _MIN_SLICES or total <= 0:
        return ""

    tone = _p(palette)
    radius = (size - thickness) / 2
    centre = size / 2
    angle = -math.pi / 2
    parts = [
        _open(size, size * 1.14),
        f'<circle cx="{_fmt(centre)}" cy="{_fmt(centre)}" r="{_fmt(radius)}" fill="none" '
        f'stroke="{tone["rule"]}" stroke-width="{_fmt(thickness)}"/>',
    ]
    gap = 0.045 if len(live) > 1 else 0.0

    for item in live:
        sweep = _TAU * (item.value / total)
        end = angle + sweep
        inner_start = angle + gap / 2
        inner_end = max(inner_start + 0.01, end - gap / 2)
        large = 1 if (inner_end - inner_start) > math.pi else 0
        x1, y1 = (
            centre + radius * math.cos(inner_start),
            centre + radius * math.sin(inner_start),
        )
        x2, y2 = (
            centre + radius * math.cos(inner_end),
            centre + radius * math.sin(inner_end),
        )
        if sweep >= _TAU - 1e-6:
            parts.append(
                f'<circle cx="{_fmt(centre)}" cy="{_fmt(centre)}" r="{_fmt(radius)}" '
                f'fill="none" stroke="{_attr(item.fill)}" stroke-width="{_fmt(thickness)}"/>'
            )
        else:
            parts.append(
                f'<path d="M {_fmt(x1)} {_fmt(y1)} A {_fmt(radius)} {_fmt(radius)} 0 {large} 1 '
                f'{_fmt(x2)} {_fmt(y2)}" fill="none" stroke="{_attr(item.fill)}" '
                f'stroke-width="{_fmt(thickness)}"/>'
            )
        angle = end

    if centre_value:
        parts.append(
            f'<text x="{_fmt(centre)}" y="{_fmt(centre - 1)}" text-anchor="middle" '
            f'dominant-baseline="middle" font-size="{_fmt(size * 0.22)}" '
            f'font-weight="600" fill="{tone["ink"]}">{escape(centre_value)}</text>'
        )
    if centre_label:
        parts.append(
            f'<text x="{_fmt(centre)}" y="{_fmt(centre + size * 0.15)}" text-anchor="middle" '
            f'font-size="{_fmt(size * 0.085)}" letter-spacing="0.08em" '
            f'fill="{tone["ink_faint"]}">{escape(centre_label)}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def stack_bar(slices: list[Slice], *, height: float = 14) -> str:
    live = [s for s in slices if s.value > 0]
    total = sum(s.value for s in live)
    if not live or total <= 0:
        return ""
    parts = [_open(_STACK_WIDTH, height)]
    x = 0.0
    usable = _STACK_WIDTH - _STACK_GAP * (len(live) - 1)
    for index, item in enumerate(live):
        span = max(2.0, usable * (item.value / total))
        parts.append(
            f'<rect x="{_fmt(x)}" y="0" width="{_fmt(span)}" height="{_fmt(height)}" '
            f'rx="2" fill="{_attr(item.fill)}"/>'
        )
        x += span + (_STACK_GAP if index < len(live) - 1 else 0)
    parts.append("</svg>")
    return "".join(parts)


def bars(
    rows: list[tuple[str, float]],
    *,
    width: float = 480,
    label_width: float = 150,
    palette: dict[str, str] | None = None,
) -> str:
    """A ranked list."""
    live = [(label, value) for label, value in rows if value is not None]
    if not live:
        return ""
    tone = _p(palette)
    fill = tone["accent"]
    top = max(value for _, value in live) or 1
    height = _BAR_ROW * len(live)
    track = width - label_width - _BAR_VALUE_WIDTH
    parts = [_open(width, height)]

    for index, (label, value) in enumerate(live):
        y = index * _BAR_ROW
        mid = y + _BAR_ROW / 2
        parts.append(
            f'<text x="0" y="{_fmt(mid)}" dominant-baseline="middle" font-size="8.4" '
            f'fill="{tone["ink"]}">{escape(clip(label or "", 34))}</text>'
        )
        span = max(1.4, track * (value / top))
        parts.append(
            f'<rect x="{_fmt(label_width)}" y="{_fmt(mid - 3.4)}" '
            f'width="{_fmt(track)}" height="6.8" rx="1.6" fill="{tone["surface"]}"/>'
        )
        parts.append(
            f'<rect x="{_fmt(label_width)}" y="{_fmt(mid - 3.4)}" '
            f'width="{_fmt(span)}" height="6.8" rx="1.6" fill="{fill}"/>'
        )
        parts.append(
            f'<text x="{_fmt(width)}" y="{_fmt(mid)}" dominant-baseline="middle" '
            f'text-anchor="end" font-size="8.4" fill="{tone["ink_soft"]}">'
            f"{escape(_number(value))}</text>"
        )
    parts.append("</svg>")
    return "".join(parts)


def dial(
    value: float,
    *,
    label: str = "",
    grade: str = "",
    arc: str = "",
    palette: dict[str, str] | None = None,
) -> str:
    """A full-circle score gauge."""
    tone = _p(palette)
    arc = _attr(arc) if arc else tone["accent"]
    size = _DIAL_SIZE
    thickness = _DIAL_THICKNESS
    ratio = max(0.0, min(1.0, value / 100))
    radius = (size - thickness) / 2 - 2
    centre = size / 2
    start = -math.pi / 2
    sweep = _TAU

    def point(fraction: float, r: float = radius) -> tuple[float, float]:
        angle = start + sweep * fraction
        return centre + r * math.cos(angle), centre + r * math.sin(angle)

    x0, y0 = point(0)
    xv, yv = point(min(ratio, 0.999))
    parts = [
        _open(size, size * 1.14),
        f'<circle cx="{_fmt(centre)}" cy="{_fmt(centre)}" r="{_fmt(radius)}" fill="none" '
        f'stroke="{tone["rule"]}" stroke-width="{_fmt(thickness)}"/>',
    ]
    if ratio >= 1:
        parts.append(
            f'<circle cx="{_fmt(centre)}" cy="{_fmt(centre)}" r="{_fmt(radius)}" fill="none" '
            f'stroke="{arc}" stroke-width="{_fmt(thickness)}"/>'
        )
    elif ratio > _ARC_EPSILON:
        large = 1 if sweep * ratio > math.pi else 0
        parts.append(
            f'<path d="M {_fmt(x0)} {_fmt(y0)} A {_fmt(radius)} {_fmt(radius)} 0 {large} 1 '
            f'{_fmt(xv)} {_fmt(yv)}" fill="none" stroke="{arc}" '
            f'stroke-width="{_fmt(thickness)}" stroke-linecap="round"/>'
        )
    parts.append(
        f'<text x="{_fmt(centre)}" y="{_fmt(centre + size * 0.055)}" text-anchor="middle" '
        f'dominant-baseline="middle" font-size="{_fmt(size * 0.34)}" font-weight="600" '
        f'letter-spacing="-0.02em" fill="{tone["ink"]}">{escape(grade or str(round(value)))}</text>'
    )
    parts.append(
        f'<text x="{_fmt(centre)}" y="{_fmt(centre + size * 0.26)}" text-anchor="middle" '
        f'font-size="{_fmt(size * 0.088)}" fill="{tone["ink_soft"]}">'
        f"{round(value)} / 100</text>"
    )
    if label:
        parts.append(
            f'<text x="{_fmt(centre)}" y="{_fmt(size * 1.09)}" text-anchor="middle" '
            f'font-size="{_fmt(size * 0.075)}" letter-spacing="0.1em" '
            f'fill="{tone["ink_faint"]}">{escape(label)}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def sparkline(
    values: list[float],
    *,
    width: float = 150,
    height: float = 30,
    palette: dict[str, str] | None = None,
) -> str:
    """The y domain starts at zero."""
    points = [v for v in values if v is not None]
    if len(points) < _MIN_POINTS:
        return ""
    tone = _p(palette)
    top = max(points) or 1
    top *= 1.12
    step = width / (len(points) - 1)
    coords = [
        (index * step, height - (value / top) * height)
        for index, value in enumerate(points)
    ]
    line = " ".join(f"{_fmt(x)},{_fmt(y)}" for x, y in coords)
    area = f"{line} {_fmt(width)},{_fmt(height)} 0,{_fmt(height)}"
    parts = [
        _open(width, height),
        f'<polygon points="{area}" fill="{tone["accent"]}" opacity="0.12"/>',
    ]
    parts.append(
        f'<polyline points="{line}" fill="none" stroke="{tone["accent"]}" '
        f'stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/>'
    )
    parts.append("</svg>")
    return "".join(parts)


def _number(value: float) -> str:
    if value >= _THOUSAND:
        return f"{int(value):,}"
    return str(int(value)) if float(value).is_integer() else f"{value:.1f}"
