from __future__ import annotations

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.report import ReportService
from reports.render.css import stylesheet
from reports.theme import ThemeError, css_variables
from reports.theme import parse as parse_theme
from shared.definitions.report_theme import ThemeTokens
from shared.definitions.reports import ReportStyle
from shared.models.report import ReportTheme

ESCAPE = "red;}body{background:url(https://example.invalid/x)}"
BREAKOUT = "</style><script>alert(1)</script>"


@pytest.mark.parametrize(
    "tokens",
    [
        {"color": {"accent": ESCAPE}},
        {"color": {"page": "#fff;color:red"}},
        {"color": {"link": "javascript:alert(1)"}},
        {"color": {"severity": {"high": ESCAPE}}},
        {"color": {"chart": ["#0091ad", ESCAPE]}},
        {"dark": {"ink": ESCAPE}},
        {"cover": {"background": ESCAPE}},
    ],
)
def test_theme_colour_must_be_hex(tokens: dict) -> None:
    with pytest.raises(ValidationError):
        ThemeTokens.model_validate(tokens)


@pytest.mark.parametrize(
    "style",
    [
        {"accent": ESCAPE},
        {"accent_soft": ESCAPE},
        {"severity_colors": {"critical": ESCAPE}},
        {"chart_palette": [ESCAPE]},
    ],
)
def test_style_colour_must_be_hex(style: dict) -> None:
    with pytest.raises(ValidationError):
        ReportStyle.model_validate(style)


def test_hex_colours_and_empty_values_pass() -> None:
    tokens = ThemeTokens.model_validate(
        {
            "color": {
                "accent": "#4F46E5",
                "page": "#fff",
                "link": "",
                "severity": {"high": "#e96500"},
                "chart": ["#0091ad"],
            },
            "cover": {"background": ""},
        }
    )
    assert "--r-accent:#4F46E5" in css_variables(tokens, ReportStyle())


@pytest.mark.parametrize(
    ("style", "values"),
    [
        ({"header_left": BREAKOUT}, {}),
        ({"footer_right": "{company}"}, {"company": BREAKOUT}),
        ({"header_center": "{target}"}, {"target": BREAKOUT.upper()}),
    ],
)
def test_slot_text_cannot_close_the_style_element(style: dict, values: dict) -> None:
    css = stylesheet(ThemeTokens(), ReportStyle.model_validate(style), values)

    assert "</" not in css
    assert "<script" not in css.lower()


def test_uploaded_theme_with_css_in_a_colour_is_refused() -> None:
    source = f"key: escape\nname: Escape\ncolor:\n  accent: '{ESCAPE}'\n"
    with pytest.raises(ThemeError):
        parse_theme(source)


async def test_themes_skips_a_stored_row_that_fails_validation(
    session: AsyncSession,
) -> None:
    service = ReportService(session)
    await service.sync_themes()
    session.add(
        ReportTheme(
            slug="stored-escape",
            name="Stored escape",
            tokens={"color": {"accent": ESCAPE}},
        )
    )
    await session.flush()

    slugs = {theme.slug for theme in (await service.catalog()).themes}

    assert "stored-escape" not in slugs
    assert slugs
