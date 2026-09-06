"""Assemble one stylesheet: faces, theme tokens, page setup, then the theme's own CSS."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from reports.theme import css_variables
from shared.definitions.report_theme import ThemeTokens
from shared.definitions.reports import (
    PAGE_SIZE_CSS,
    SLOT_TOKEN_VALUES,
    Orientation,
    ReportStyle,
)

ASSETS = Path(__file__).resolve().parent.parent / "assets"
TEMPLATES = Path(__file__).resolve().parent.parent / "templates"

_TOKEN_RE = re.compile("(" + "|".join(re.escape(t) for t in SLOT_TOKEN_VALUES) + ")")

# how much air sits between a running head and the text block
RUNNING_CLEAR = 8.0

_COUNTER_SLOTS = {
    "{page}": "counter(page)",
    "{pages}": "counter(pages)",
    "{section}": "string(section)",
}


@lru_cache(maxsize=1)
def base_css() -> str:
    return (TEMPLATES / "base.css").read_text(encoding="utf-8")


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def slot_content(template: str, values: dict[str, str]) -> str:
    """A header or footer slot as a CSS content value."""
    if not template.strip():
        return "none"
    parts: list[str] = []
    for piece in _TOKEN_RE.split(template):
        if not piece:
            continue
        if piece in _COUNTER_SLOTS:
            parts.append(_COUNTER_SLOTS[piece])
        elif piece.startswith("{") and piece.endswith("}"):
            literal = values.get(piece[1:-1], "")
            if literal:
                parts.append(f'"{_escape(literal)}"')
        else:
            parts.append(f'"{_escape(piece)}"')
    return " ".join(parts) if parts else "none"


def page_css(style: ReportStyle, values: dict[str, str]) -> str:
    size = PAGE_SIZE_CSS.get(style.page_size, "A4")
    orientation = (
        "landscape" if style.orientation == Orientation.LANDSCAPE.value else "portrait"
    )
    margins = (
        f"{style.margin_top}mm {style.margin_right}mm "
        f"{style.margin_bottom}mm {style.margin_left}mm"
    )

    boxes: list[str] = []
    slots = (
        ("top-left", style.header_left if style.show_header else ""),
        ("top-center", style.header_center if style.show_header else ""),
        ("top-right", style.header_right if style.show_header else ""),
        ("bottom-left", style.footer_left if style.show_footer else ""),
        ("bottom-center", style.footer_center if style.show_footer else ""),
        ("bottom-right", style.footer_right if style.show_footer else ""),
    )
    # A running head belongs against the text block, not against the paper's edge: the
    # top boxes sit on the bottom of their margin, the bottom boxes on the top of theirs.
    for box, template in slots:
        content = slot_content(template, values)
        if content == "none":
            continue
        at_top = box.startswith("top")
        boxes.append(
            f"@{box}{{content:{content};font-family:var(--r-font-body);"
            f"font-size:var(--r-micro);letter-spacing:var(--r-run-track);"
            f"color:var(--r-ink-faint);white-space:nowrap;"
            f"padding-{'bottom' if at_top else 'top'}:{RUNNING_CLEAR}mm;"
            f"vertical-align:{'bottom' if at_top else 'top'}}}"
        )

    blank = "".join(
        f"@{box}{{content:none}}"
        for box in (
            "top-left",
            "top-center",
            "top-right",
            "bottom-left",
            "bottom-center",
            "bottom-right",
        )
    )

    return (
        f"@page{{size:{size} {orientation};margin:{margins};background:var(--r-page);{''.join(boxes)}}}"
        f"@page cover{{margin:0;background:var(--r-page);{blank}}}"
        f"@page appendix{{{''.join(boxes)}}}"
        "h1{bookmark-level:1;bookmark-label:content(text)}"
        ".section__title{string-set:section attr(data-run);bookmark-level:1;bookmark-label:attr(data-run)}"
        ".sub__title{bookmark-level:2;bookmark-label:content(text)}"
        ".finding__title{bookmark-level:3;bookmark-label:content(text)}"
    )


def stylesheet(
    tokens: ThemeTokens,
    style: ReportStyle,
    values: dict[str, str],
    *,
    faces: str = "",
    families: dict[str, str] | None = None,
) -> str:
    return "\n".join(
        (
            faces,
            css_variables(tokens, style, families=families),
            base_css(),
            page_css(style, values),
            tokens.css or "",
        )
    )
