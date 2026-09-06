"""Themes are token files. This turns one into the CSS custom properties the document reads."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml

from shared.definitions.report_theme import ColorTokens, ThemeTokens
from shared.definitions.reports import (
    DARK_CHART_PALETTE,
    DARK_SEVERITY_COLORS,
    DEFAULT_CHART_PALETTE,
    DEFAULT_SEVERITY_COLORS,
    DENSITY_SCALE,
    FONT_BY_KEY,
    ReportStyle,
)
from shared.utils.color import ink as ink_of
from shared.utils.color import is_dark, mix
from shared.utils.color import tint as tint_of

THEME_DIR = Path(__file__).resolve().parent / "themes"

_FALLBACK_CHART = list(DEFAULT_CHART_PALETTE)
_MONO_CHART = ["#22262e", "#474d58", "#6d7481", "#9aa1ad", "#c6ccd5"]
_MONO_SEVERITY = {
    "critical": "#14181f",
    "high": "#3b414c",
    "medium": "#666d79",
    "low": "#98a0ac",
    "info": "#c3c9d2",
    "unknown": "#c3c9d2",
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

    paper_is_dark = is_dark(colour.page)
    base_severity = DARK_SEVERITY_COLORS if paper_is_dark else DEFAULT_SEVERITY_COLORS
    colour.severity = {**base_severity, **colour.severity}
    if not colour.chart:
        colour.chart = list(
            DARK_CHART_PALETTE if paper_is_dark else DEFAULT_CHART_PALETTE
        )
    if not colour.link:
        colour.link = colour.accent
    return merged


def _wash(value: str, page: str) -> str:
    """A badge ground: a tint on light paper, the colour dropped into dark paper."""
    return mix(page, value, 0.20) if is_dark(page) else tint_of(value)


def _label_ink(value: str, page: str) -> str:
    """Text that sits on that ground."""
    return value if is_dark(page) else ink_of(value)


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
        "small": round(base * 0.87, 2),
        "micro": round(base * 0.775, 2),
        "gap": round(0.92 * tighten, 3),
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
        f"--r-label-case:{'uppercase' if typography.uppercase_labels else 'none'}",
        f"--r-run-track:{round(typography.label_tracking * 0.35, 4)}em",
        f"--r-align:{'justify' if style.justify else 'left'}",
        f"--r-hyphens:{'auto' if style.hyphenate else 'manual'}",
        f"--r-chapter-break:{'page' if style.chapter_breaks else 'auto'}",
        f"--r-chapter-rule:{'0' if style.chapter_breaks else 'var(--r-rule-w) solid var(--r-rule)'}",
        f"--r-chapter-pad:{'0' if style.chapter_breaks else 'calc(var(--r-block-gap) * 1.6)'}",
        f"--r-rule-w:{layout.rule_width}pt",
        f"--r-radius:{layout.radius}px",
        f"--r-pill:{'999px' if layout.pill else f'{layout.radius}px'}",
        f"--r-block-gap:{round(layout.block_gap, 3)}rem",
        f"--r-chart-stroke:{layout.chart_stroke}",
        f"--r-watermark-opacity:{style.watermark_opacity}",
    ]
    for key, value in colour.severity.items():
        lines.append(f"--r-sev-{key}:{value}")
        lines.append(f"--r-sev-{key}-wash:{_wash(value, colour.page)}")
        lines.append(f"--r-sev-{key}-ink:{_label_ink(value, colour.page)}")
    for index, value in enumerate(colour.chart[:8], start=1):
        lines.append(f"--r-chart-{index}:{value}")
    lines.append(f"--r-accent-wash:{_wash(colour.accent, colour.page)}")
    lines.append(f"--r-accent-ink-on-wash:{_label_ink(colour.accent, colour.page)}")

    body = ";".join(lines)
    return f":root{{{body}}}"


def theme_summary(tokens: ThemeTokens, origin: str) -> dict:
    colour = tokens.color
    dark_paper = is_dark(colour.page)
    severity = DARK_SEVERITY_COLORS if dark_paper else DEFAULT_SEVERITY_COLORS
    chart = DARK_CHART_PALETTE if dark_paper else DEFAULT_CHART_PALETTE
    return {
        "slug": tokens.key,
        "name": tokens.name,
        "description": tokens.description,
        "author": tokens.author,
        "origin": origin,
        "accent": colour.accent,
        "page": colour.page,
        "ink": colour.ink,
        "ink_soft": colour.ink_soft,
        "ink_faint": colour.ink_faint,
        "rule": colour.rule,
        "surface": colour.surface,
        "cover_background": tokens.cover.background or colour.accent,
        "cover_ink": "#ffffff" if tokens.cover.ink == "light" else colour.ink,
        "cover_layout": tokens.cover.layout,
        "cover_art": tokens.cover.art,
        "heading_font": tokens.type.heading,
        "body_font": tokens.type.body,
        "mono_font": tokens.type.mono,
        "heading_style": tokens.layout.heading,
        "table_style": tokens.layout.table,
        "finding_style": tokens.layout.finding,
        "radius": tokens.layout.radius,
        "uppercase_labels": tokens.type.uppercase_labels,
        "severity": {**severity, **colour.severity},
        "chart": list(colour.chart or chart),
    }
