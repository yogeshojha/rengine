"""Cover artwork. Drawn in the cover's own ink so a theme change restyles it."""

from __future__ import annotations

import math

from shared.definitions.report_theme import CoverArt

_W = 210.0
_H = 297.0
_FADE_FLOOR = 0.02
# where the grade mark sits, so artwork can centre on it
MARK_X = 171.0
MARK_Y = 42.0


def _wrap(body: str) -> str:
    return (
        f'<svg viewBox="0 0 {_W:.0f} {_H:.0f}" preserveAspectRatio="xMidYMid slice" '
        f'aria-hidden="true">{body}</svg>'
    )


def _grid(accent: str) -> str:
    fine = []
    for x in range(0, int(_W) + 1, 5):
        fine.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{_H:.0f}"/>')
    for y in range(0, int(_H) + 1, 5):
        fine.append(f'<line x1="0" y1="{y}" x2="{_W:.0f}" y2="{y}"/>')
    coarse = []
    for x in range(0, int(_W) + 1, 25):
        coarse.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{_H:.0f}"/>')
    for y in range(0, int(_H) + 1, 25):
        coarse.append(f'<line x1="0" y1="{y}" x2="{_W:.0f}" y2="{y}"/>')
    # a reticle around the grade mark: the blueprint's own instrument
    rings = "".join(
        f'<circle cx="{MARK_X}" cy="{MARK_Y}" r="{r}"/>' for r in (24, 34, 46, 60)
    )
    ticks = []
    for index in range(36):
        angle = math.radians(index * 10)
        inner = 46 if index % 9 else 40
        x1, y1 = MARK_X + inner * math.cos(angle), MARK_Y + inner * math.sin(angle)
        x2, y2 = MARK_X + 60 * math.cos(angle), MARK_Y + 60 * math.sin(angle)
        ticks.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>')
    cross = (
        f'<line x1="{MARK_X - 72}" y1="{MARK_Y}" x2="{MARK_X + 72}" y2="{MARK_Y}"/>'
        f'<line x1="{MARK_X}" y1="{MARK_Y - 72}" x2="{MARK_X}" y2="{MARK_Y + 72}"/>'
    )
    return _wrap(
        f'<g stroke="currentColor" stroke-width="0.12" opacity="0.14">{"".join(fine)}</g>'
        f'<g stroke="currentColor" stroke-width="0.22" opacity="0.2">{"".join(coarse)}</g>'
        f'<g fill="none" stroke="{accent}" stroke-width="0.35" opacity="0.55">{rings}</g>'
        f'<g stroke="{accent}" stroke-width="0.3" opacity="0.5">{"".join(ticks)}</g>'
        f'<g stroke="{accent}" stroke-width="0.25" opacity="0.35">{cross}</g>'
    )


def _scan(accent: str) -> str:
    lines = [
        f'<line x1="0" y1="{y}" x2="{_W:.0f}" y2="{y}"/>'
        for y in range(0, int(_H) + 1, 3)
    ]
    # a cursor bar down the left edge and a faint block of glyphs top-right
    glyphs = []
    for row in range(14):
        for col in range(18):
            x = 112 + col * 5.2
            y = 24 + row * 6.2
            fade = max(0.0, 1 - ((col - 17) ** 2 + (row - 1) ** 2) / 160)
            if fade <= _FADE_FLOOR:
                continue
            char = "0" if (row * 7 + col * 3) % 5 else "1"
            glyphs.append(
                f'<text x="{x:.1f}" y="{y:.1f}" font-family="monospace" font-size="4.2" '
                f'opacity="{fade * 0.32:.2f}">{char}</text>'
            )
    return _wrap(
        f'<g stroke="currentColor" stroke-width="0.35" opacity="0.08">{"".join(lines)}</g>'
        f'<g fill="currentColor">{"".join(glyphs)}</g>'
        f'<rect x="0" y="0" width="3.2" height="{_H:.0f}" fill="{accent}"/>'
    )


def _rings(accent: str) -> str:
    circles = [f'<circle cx="228" cy="58" r="{r}"/>' for r in range(18, 240, 16)]
    return _wrap(
        f'<g fill="none" stroke="currentColor" stroke-width="0.32" opacity="0.18">'
        f"{''.join(circles)}</g>"
        f'<g fill="none" stroke="{accent}" stroke-width="0.7" opacity="0.55">'
        f'<circle cx="228" cy="58" r="98"/></g>'
    )


def _topo(accent: str) -> str:
    paths = []
    for index in range(16):
        offset = -10 + index * 22
        amplitude = 10 + index * 1.6
        points = []
        for step in range(0, int(_W) + 6, 4):
            y = (
                offset
                + amplitude * math.sin(step / 31.0 + index * 0.6)
                + 5 * math.sin(step / 9.0)
            )
            points.append(f"{step},{y:.1f}")
        paths.append(f'<polyline points="{" ".join(points)}"/>')
    lit = paths[6]
    return _wrap(
        f'<g fill="none" stroke="currentColor" stroke-width="0.3" opacity="0.16">'
        f"{''.join(paths)}</g>"
        f'<g fill="none" stroke="{accent}" stroke-width="0.7" opacity="0.6">{lit}</g>'
    )


def _mesh(accent: str) -> str:
    dots = []
    for row in range(40):
        for column in range(30):
            x = column * 8 + (4 if row % 2 else 0)
            y = row * 8
            fade = max(0.0, 1 - ((x - 205) ** 2 + (y - 30) ** 2) / 52000)
            if fade <= _FADE_FLOOR:
                continue
            dots.append(
                f'<circle cx="{x}" cy="{y}" r="0.7" opacity="{fade * 0.55:.2f}"/>'
            )
    rings = "".join(
        f'<circle cx="{MARK_X + 8}" cy="{MARK_Y - 4}" r="{r}"/>' for r in (52, 88, 130)
    )
    return _wrap(
        f'<g fill="currentColor">{"".join(dots)}</g>'
        f'<g fill="none" stroke="{accent}" stroke-width="0.6" opacity="0.5">{rings}</g>'
        f'<g fill="none" stroke="{accent}" stroke-width="1.6" opacity="0.9">'
        f'<path d="M {MARK_X + 8 - 130} {MARK_Y - 4} A 130 130 0 0 1 {MARK_X + 8} {MARK_Y - 4 - 130}"/></g>'
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
