"""Cover artwork. Drawn in the cover's own ink so a theme change restyles it."""

from __future__ import annotations

import math

from shared.definitions.report_theme import CoverArt

_W = 210.0
_H = 297.0
_FADE_FLOOR = 0.02


def _wrap(body: str) -> str:
    return (
        f'<svg viewBox="0 0 {_W:.0f} {_H:.0f}" preserveAspectRatio="xMidYMid slice" '
        f'aria-hidden="true">{body}</svg>'
    )


def _grid(accent: str) -> str:  # noqa: ARG001
    lines = []
    for x in range(0, int(_W) + 1, 7):
        lines.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{_H:.0f}"/>')
    for y in range(0, int(_H) + 1, 7):
        lines.append(f'<line x1="0" y1="{y}" x2="{_W:.0f}" y2="{y}"/>')
    return _wrap(
        f'<g stroke="currentColor" stroke-width="0.18" opacity="0.13">{"".join(lines)}</g>'
    )


def _scan(accent: str) -> str:
    lines = [
        f'<line x1="0" y1="{y}" x2="{_W:.0f}" y2="{y}"/>'
        for y in range(0, int(_H) + 1, 3)
    ]
    return _wrap(
        f'<g stroke="currentColor" stroke-width="0.35" opacity="0.09">{"".join(lines)}</g>'
        f'<g stroke="{accent}" stroke-width="0.8" opacity="0.5">'
        f'<line x1="0" y1="196" x2="{_W:.0f}" y2="196"/></g>'
    )


def _rings(accent: str) -> str:  # noqa: ARG001
    circles = [f'<circle cx="168" cy="70" r="{r}"/>' for r in range(14, 150, 13)]
    return _wrap(
        f'<g fill="none" stroke="currentColor" stroke-width="0.3" opacity="0.16">'
        f"{''.join(circles)}</g>"
    )


def _topo(accent: str) -> str:  # noqa: ARG001
    paths = []
    for index in range(11):
        offset = 26 + index * 20
        amplitude = 9 + index * 1.5
        points = []
        for step in range(0, int(_W) + 6, 6):
            y = offset + amplitude * math.sin(step / 34.0 + index * 0.55)
            points.append(f"{step},{y:.1f}")
        paths.append(f'<polyline points="{" ".join(points)}"/>')
    return _wrap(
        f'<g fill="none" stroke="currentColor" stroke-width="0.3" opacity="0.15">'
        f"{''.join(paths)}</g>"
    )


def _mesh(accent: str) -> str:
    dots = []
    for row in range(30):
        for column in range(22):
            x = column * 10 + (5 if row % 2 else 0)
            y = row * 10
            fade = max(0.0, 1 - ((x - 190) ** 2 + (y - 40) ** 2) / 62000)
            if fade <= _FADE_FLOOR:
                continue
            dots.append(
                f'<circle cx="{x}" cy="{y}" r="0.75" opacity="{fade * 0.5:.2f}"/>'
            )
    return _wrap(
        f'<g fill="currentColor">{"".join(dots)}</g>'
        f'<g fill="none" stroke="{accent}" stroke-width="0.5" opacity="0.35">'
        f'<circle cx="190" cy="40" r="46"/><circle cx="190" cy="40" r="74"/></g>'
    )


_ART = {
    CoverArt.GRID.value: _grid,
    CoverArt.SCAN.value: _scan,
    CoverArt.RINGS.value: _rings,
    CoverArt.TOPO.value: _topo,
    CoverArt.MESH.value: _mesh,
}


def cover_art(kind: str, accent: str = "#4f46e5") -> str:
    builder = _ART.get(kind)
    return builder(accent) if builder else ""
