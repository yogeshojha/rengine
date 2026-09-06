"""Charts are SVG built here, coloured by CSS variables, so a theme reskins them for free."""

from __future__ import annotations

import math
from dataclasses import dataclass
from html import escape

_TAU = math.pi * 2
_MIN_SLICES = 2
_MIN_POINTS = 2
_ARC_EPSILON = 0.005
_DARK_CELL = 0.55
_THOUSAND = 1000

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
    return {**DEFAULT_PALETTE, **(palette or {})}


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
    """A ring. Two slices or fewer is a statistic, not a chart, so it is refused."""
    live = [s for s in slices if s.value > 0]
    total = sum(s.value for s in live)
    if len(live) < _MIN_SLICES or total <= 0:
        return ""

    tone = _p(palette)
    radius = (size - thickness) / 2
    centre = size / 2
    angle = -math.pi / 2
    parts = [_open(size, size)]
    gap = 0.035 if len(live) > 1 else 0.0

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
                f'fill="none" stroke="{item.fill}" stroke-width="{_fmt(thickness)}"/>'
            )
        else:
            parts.append(
                f'<path d="M {_fmt(x1)} {_fmt(y1)} A {_fmt(radius)} {_fmt(radius)} 0 {large} 1 '
                f'{_fmt(x2)} {_fmt(y2)}" fill="none" stroke="{item.fill}" '
                f'stroke-width="{_fmt(thickness)}"/>'
            )
        angle = end

    if centre_value:
        parts.append(
            f'<text x="{_fmt(centre)}" y="{_fmt(centre - 1)}" text-anchor="middle" '
            f'dominant-baseline="middle" font-size="{_fmt(size * 0.22)}" '
            f'font-weight="650" fill="{tone["ink"]}">{escape(centre_value)}</text>'
        )
    if centre_label:
        parts.append(
            f'<text x="{_fmt(centre)}" y="{_fmt(centre + size * 0.15)}" text-anchor="middle" '
            f'font-size="{_fmt(size * 0.085)}" letter-spacing="0.08em" '
            f'fill="{tone["ink_faint"]}">{escape(centre_label.upper())}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def stack_bar(
    slices: list[Slice], *, width: float = 480, height: float = 14, gap: float = 1.5
) -> str:
    live = [s for s in slices if s.value > 0]
    total = sum(s.value for s in live)
    if not live or total <= 0:
        return ""
    parts = [_open(width, height)]
    x = 0.0
    usable = width - gap * (len(live) - 1)
    for index, item in enumerate(live):
        span = max(2.0, usable * (item.value / total))
        parts.append(
            f'<rect x="{_fmt(x)}" y="0" width="{_fmt(span)}" height="{_fmt(height)}" '
            f'rx="2" fill="{item.fill}"/>'
        )
        x += span + (gap if index < len(live) - 1 else 0)
    parts.append("</svg>")
    return "".join(parts)


def bars(
    rows: list[tuple[str, float]],
    *,
    width: float = 480,
    row_height: float = 17,
    label_width: float = 150,
    value_width: float = 44,
    fill: str = "",
    suffix: str = "",
    palette: dict[str, str] | None = None,
) -> str:
    """A ranked list. One hue for every bar; rank is carried by order, never by colour."""
    live = [(label, value) for label, value in rows if value is not None]
    if not live:
        return ""
    tone = _p(palette)
    fill = fill or tone["accent"]
    top = max(value for _, value in live) or 1
    height = row_height * len(live)
    track = width - label_width - value_width
    parts = [_open(width, height)]

    for index, (label, value) in enumerate(live):
        y = index * row_height
        mid = y + row_height / 2
        parts.append(
            f'<text x="0" y="{_fmt(mid)}" dominant-baseline="middle" font-size="8.4" '
            f'fill="{tone["ink"]}">{escape(_clip(label, 34))}</text>'
        )
        span = max(1.4, track * (value / top))
        parts.append(
            f'<rect x="{_fmt(label_width)}" y="{_fmt(y + row_height / 2 - 3.4)}" '
            f'width="{_fmt(track)}" height="6.8" rx="1.6" fill="{tone["surface"]}"/>'
        )
        parts.append(
            f'<rect x="{_fmt(label_width)}" y="{_fmt(y + row_height / 2 - 3.4)}" '
            f'width="{_fmt(span)}" height="6.8" rx="1.6" fill="{fill}"/>'
        )
        parts.append(
            f'<text x="{_fmt(width)}" y="{_fmt(mid)}" dominant-baseline="middle" '
            f'text-anchor="end" font-size="8.4" fill="{tone["ink_soft"]}">'
            f"{escape(_number(value))}{escape(suffix)}</text>"
        )
    parts.append("</svg>")
    return "".join(parts)


def dial(
    value: float,
    *,
    size: float = 120,
    thickness: float = 12,
    label: str = "",
    grade: str = "",
    arc: str = "",
    palette: dict[str, str] | None = None,
) -> str:
    """A 240 degree gauge. The grade is the message; the arc is the scale."""
    tone = _p(palette)
    arc = arc or tone["accent"]
    ratio = max(0.0, min(1.0, value / 100))
    radius = (size - thickness) / 2 - 2
    centre = size / 2
    start = math.pi * 5 / 6
    sweep = math.pi * 4 / 3

    def point(fraction: float, r: float = radius) -> tuple[float, float]:
        angle = start + sweep * fraction
        return centre + r * math.cos(angle), centre + r * math.sin(angle)

    x0, y0 = point(0)
    x1, y1 = point(1)
    xv, yv = point(ratio)
    parts = [
        _open(size, size * 0.9),
        f'<path d="M {_fmt(x0)} {_fmt(y0)} A {_fmt(radius)} {_fmt(radius)} 0 1 1 {_fmt(x1)} {_fmt(y1)}" '
        f'fill="none" stroke="{tone["surface"]}" stroke-width="{_fmt(thickness)}" stroke-linecap="round"/>',
    ]
    if ratio > _ARC_EPSILON:
        large = 1 if sweep * ratio > math.pi else 0
        parts.append(
            f'<path d="M {_fmt(x0)} {_fmt(y0)} A {_fmt(radius)} {_fmt(radius)} 0 {large} 1 '
            f'{_fmt(xv)} {_fmt(yv)}" fill="none" stroke="{arc}" '
            f'stroke-width="{_fmt(thickness)}" stroke-linecap="round"/>'
        )
    # tick marks at the quartiles keep the scale honest without an axis
    for fraction in (0.25, 0.5, 0.75):
        ax, ay = point(fraction, radius - thickness / 2 - 3)
        bx, by = point(fraction, radius - thickness / 2 - 6)
        parts.append(
            f'<line x1="{_fmt(ax)}" y1="{_fmt(ay)}" x2="{_fmt(bx)}" y2="{_fmt(by)}" '
            f'stroke="{tone["rule"]}" stroke-width="1"/>'
        )
    parts.append(
        f'<text x="{_fmt(centre)}" y="{_fmt(centre + size * 0.02)}" text-anchor="middle" '
        f'dominant-baseline="middle" font-size="{_fmt(size * 0.36)}" font-weight="700" '
        f'letter-spacing="-0.02em" fill="{tone["ink"]}">{escape(grade or str(round(value)))}</text>'
    )
    parts.append(
        f'<text x="{_fmt(centre)}" y="{_fmt(centre + size * 0.24)}" text-anchor="middle" '
        f'font-size="{_fmt(size * 0.085)}" fill="{tone["ink_soft"]}">'
        f"{round(value)} / 100</text>"
    )
    if label:
        parts.append(
            f'<text x="{_fmt(centre)}" y="{_fmt(centre + size * 0.4)}" text-anchor="middle" '
            f'font-size="{_fmt(size * 0.075)}" letter-spacing="0.1em" '
            f'fill="{tone["ink_faint"]}">{escape(label.upper())}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def sparkline(
    values: list[float],
    *,
    width: float = 150,
    height: float = 30,
    fill: bool = True,
    palette: dict[str, str] | None = None,
) -> str:
    """The y domain starts at zero, so flat data reads as flat."""
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
    parts = [_open(width, height)]
    if fill:
        area = f"{line} {_fmt(width)},{_fmt(height)} 0,{_fmt(height)}"
        parts.append(
            f'<polygon points="{area}" fill="{tone["accent"]}" opacity="0.12"/>'
        )
    parts.append(
        f'<polyline points="{line}" fill="none" stroke="{tone["accent"]}" '
        f'stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/>'
    )
    parts.append("</svg>")
    return "".join(parts)


def matrix(
    columns: list[str],
    rows: list[str],
    cells: dict[tuple[int, int], float],
    *,
    width: float = 480,
    row_height: float = 18,
    label_width: float = 120,
    palette: dict[str, str] | None = None,
) -> str:
    if not rows or not columns:
        return ""
    tone = _p(palette)
    top = max(cells.values()) if cells else 0
    if top <= 0:
        return ""
    head = 14.0
    cell_width = (width - label_width) / len(columns)
    height = head + row_height * len(rows)
    parts = [_open(width, height)]

    for index, column in enumerate(columns):
        x = label_width + cell_width * index + cell_width / 2
        parts.append(
            f'<text x="{_fmt(x)}" y="8" text-anchor="middle" font-size="7" '
            f'letter-spacing="0.06em" fill="{tone["ink_faint"]}">'
            f"{escape(_clip(column.upper(), 12))}</text>"
        )

    for r, row in enumerate(rows):
        y = head + r * row_height
        parts.append(
            f'<text x="0" y="{_fmt(y + row_height / 2)}" dominant-baseline="middle" '
            f'font-size="8.4" fill="{tone["ink"]}">{escape(_clip(row, 26))}</text>'
        )
        for c in range(len(columns)):
            value = cells.get((r, c), 0)
            x = label_width + cell_width * c
            opacity = 0.08 + 0.82 * (value / top) if value else 0.0
            parts.append(
                f'<rect x="{_fmt(x + 1)}" y="{_fmt(y + 1.5)}" width="{_fmt(cell_width - 2)}" '
                f'height="{_fmt(row_height - 3)}" rx="1.5" fill="{tone["accent"]}" '
                f'opacity="{_fmt(opacity)}"/>'
            )
            if value:
                parts.append(
                    f'<text x="{_fmt(x + cell_width / 2)}" y="{_fmt(y + row_height / 2)}" '
                    f'text-anchor="middle" dominant-baseline="middle" font-size="7.6" '
                    f'fill="{tone["accent_ink"] if opacity > _DARK_CELL else tone["ink"]}">'
                    f"{int(value)}</text>"
                )
    parts.append("</svg>")
    return "".join(parts)


def _clip(value: str, length: int) -> str:
    text = value or ""
    return text if len(text) <= length else text[: length - 1] + "…"


def _number(value: float) -> str:
    if value >= _THOUSAND:
        return f"{int(value):,}"
    return str(int(value)) if float(value).is_integer() else f"{value:.1f}"
