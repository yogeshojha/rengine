"""Themes are token files. This turns one into the CSS custom properties the document reads."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml

from shared.definitions.report_theme import ColorTokens, ThemeTokens
from shared.definitions.reports import (
    DEFAULT_SEVERITY_COLORS,
    DENSITY_SCALE,
    FONT_BY_KEY,
    ReportStyle,
)

THEME_DIR = Path(__file__).resolve().parent / "themes"

_FALLBACK_CHART = ["#4f46e5", "#0d9488", "#7c3aed", "#d97706", "#0891b2"]
_MONO_CHART = ["#2c2f36", "#4d525c", "#6f7581", "#9aa0ab", "#c2c7d0"]
_MONO_SEVERITY = {
    "critical": "#16181d",
    "high": "#3a3e46",
    "medium": "#6b707b",
    "low": "#9aa0ab",
    "info": "#c2c7d0",
    "unknown": "#c2c7d0",
}


class ThemeError(ValueError):
    """A theme file could not be read."""


_IMPORT_RE = re.compile(r"@import\b", re.I)
_URL_RE = re.compile(r"url\(\s*['\"]?([^)'\"]*)", re.I)


def check_css(css: str) -> None:
    """A theme may style, never fetch. Anything that could pull bytes is refused."""
    if not css:
        return
    if _IMPORT_RE.search(css):
        msg = "A theme may not use @import. Put the rules in the css block itself."
        raise ThemeError(msg)
    for target in _URL_RE.findall(css):
        if not target.strip().lower().startswith("data:"):
            msg = (
                "A theme may only reference embedded data in url(). "
                f"Refused: {target.strip()[:80] or '(empty)'}"
            )
            raise ThemeError(msg)


def parse(source: str, *, slug: str = "") -> ThemeTokens:
    try:
        raw = yaml.safe_load(source)
    except yaml.YAMLError as exc:
        msg = f"Not valid YAML: {exc}"
        raise ThemeError(msg) from exc
    if not isinstance(raw, dict):
        msg = "A theme file must be a mapping of tokens."
        raise ThemeError(msg)
    try:
        tokens = ThemeTokens.model_validate(raw)
    except ValueError as exc:
        msg = f"Not a valid theme: {exc}"
        raise ThemeError(msg) from exc
    if slug:
        tokens.key = slug
    if not tokens.key:
        msg = "A theme needs a key."
        raise ThemeError(msg)
    if not tokens.name:
        tokens.name = tokens.key.replace("-", " ").title()
    check_css(tokens.css)
    return tokens


@lru_cache(maxsize=1)
def builtin_themes() -> dict[str, ThemeTokens]:
    out: dict[str, ThemeTokens] = {}
    if not THEME_DIR.is_dir():
        return out
    for path in sorted(THEME_DIR.glob("*.yaml")):
        tokens = parse(path.read_text(encoding="utf-8"), slug=path.stem)
        out[tokens.key] = tokens
    return out


def builtin_source(slug: str) -> str:
    path = THEME_DIR / f"{slug}.yaml"
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def resolve(tokens: ThemeTokens, style: ReportStyle) -> ThemeTokens:
    """Apply the report's own overrides on top of the theme."""
    merged = tokens.model_copy(deep=True)
    colour = merged.color

    if style.accent:
        colour.accent = style.accent
    if style.accent_soft:
        colour.accent_soft = style.accent_soft
    if style.severity_colors:
        colour.severity = {**colour.severity, **style.severity_colors}
    if style.chart_palette:
        colour.chart = list(style.chart_palette)
    if style.heading_font:
        merged.type.heading = style.heading_font
    if style.body_font:
        merged.type.body = style.body_font
    if style.mono_font:
        merged.type.mono = style.mono_font
    if style.cover_layout:
        merged.cover.layout = style.cover_layout

    merged.type.base_size = style.base_font_size
    merged.type.line_height = style.line_height

    if style.mono_safe:
        colour.chart = list(_MONO_CHART)
        colour.severity = dict(_MONO_SEVERITY)
        colour.accent = "#2c2f36"
        colour.accent_soft = "#eeeff2"
        merged.cover.art = "none"

    colour.severity = {**DEFAULT_SEVERITY_COLORS, **colour.severity}
    if not colour.chart:
        colour.chart = list(_FALLBACK_CHART)
    if not colour.link:
        colour.link = colour.accent
    return merged


def _snap_weight(value: int) -> int:
    """WeasyPrint accepts only the hundreds, so 650 must become 700 rather than nothing."""
    return max(100, min(900, round(value / 100) * 100))


def font_stack(key: str, fallback: str, families: dict[str, str] | None = None) -> str:
    family = (families or {}).get(key) or (
        FONT_BY_KEY[key].stack if key in FONT_BY_KEY else key
    )
    return f"'{family}', {fallback}" if family else fallback


def _scale_sizes(base: float, ratio: float, density: str) -> dict[str, float]:
    tighten = DENSITY_SCALE.get(density, 1.0)
    return {
        "h1": round(base * ratio**3, 2),
        "h2": round(base * ratio**2, 2),
        "h3": round(base * ratio, 2),
        "h4": round(base * 1.06, 2),
        "small": round(base * 0.86, 2),
        "micro": round(base * 0.74, 2),
        "gap": round(0.9 * tighten, 3),
    }


def css_variables(
    tokens: ThemeTokens, style: ReportStyle, *, families: dict[str, str] | None = None
) -> str:
    colour: ColorTokens = tokens.color
    typography = tokens.type
    layout = tokens.layout
    sizes = _scale_sizes(typography.base_size, typography.scale, style.density)

    lines = [
        f"--r-page:{colour.page}",
        f"--r-ink:{colour.ink}",
        f"--r-ink-soft:{colour.ink_soft}",
        f"--r-ink-faint:{colour.ink_faint}",
        f"--r-rule:{colour.rule}",
        f"--r-rule-strong:{colour.rule_strong}",
        f"--r-surface:{colour.surface}",
        f"--r-surface-soft:{colour.surface_soft}",
        f"--r-accent:{colour.accent}",
        f"--r-accent-soft:{colour.accent_soft}",
        f"--r-accent-ink:{colour.accent_ink}",
        f"--r-link:{colour.link}",
        f"--r-cover-bg:{tokens.cover.background or colour.accent}",
        f"--r-cover-ink:{'#ffffff' if tokens.cover.ink == 'light' else colour.ink}",
        f"--r-font-heading:{font_stack(typography.heading, 'sans-serif', families)}",
        f"--r-font-body:{font_stack(typography.body, 'sans-serif', families)}",
        f"--r-font-mono:{font_stack(typography.mono, 'monospace', families)}",
        f"--r-size:{typography.base_size}pt",
        f"--r-lh:{typography.line_height}",
        f"--r-h1:{sizes['h1']}pt",
        f"--r-h2:{sizes['h2']}pt",
        f"--r-h3:{sizes['h3']}pt",
        f"--r-h4:{sizes['h4']}pt",
        f"--r-small:{sizes['small']}pt",
        f"--r-micro:{sizes['micro']}pt",
        f"--r-gap:{sizes['gap']}rem",
        f"--r-h-weight:{_snap_weight(typography.heading_weight)}",
        f"--r-h-track:{typography.heading_tracking}em",
        f"--r-label-track:{typography.label_tracking}em",
        f"--r-rule-w:{layout.rule_width}pt",
        f"--r-radius:{layout.radius}px",
        f"--r-block-gap:{round(layout.block_gap, 3)}rem",
        f"--r-chart-stroke:{layout.chart_stroke}",
        f"--r-watermark-opacity:{style.watermark_opacity}",
    ]
    for key, value in colour.severity.items():
        lines.append(f"--r-sev-{key}:{value}")
    for index, value in enumerate(colour.chart[:8], start=1):
        lines.append(f"--r-chart-{index}:{value}")

    body = ";".join(lines)
    return f":root{{{body}}}"


def theme_summary(tokens: ThemeTokens, origin: str) -> dict:
    return {
        "slug": tokens.key,
        "name": tokens.name,
        "description": tokens.description,
        "author": tokens.author,
        "origin": origin,
        "accent": tokens.color.accent,
        "page": tokens.color.page,
        "ink": tokens.color.ink,
        "cover_layout": tokens.cover.layout,
        "heading_font": tokens.type.heading,
        "body_font": tokens.type.body,
        "severity": {**DEFAULT_SEVERITY_COLORS, **tokens.color.severity},
        "chart": list(tokens.color.chart or _FALLBACK_CHART),
    }
