"""A report theme is data: tokens a user can write, upload and share."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator

from shared.definitions.vulnerabilities import SEVERITY_ORDER

MAX_THEME_BYTES = 200_000
MAX_THEME_CSS = 60_000
THEME_SLUG_LENGTH = 48

_HEX_COLOR = re.compile(r"#(?:[0-9a-fA-F]{3}){1,2}")
_FONT_KEY = re.compile(r"(?:[^\W_]|-)*")


def _color(value: str) -> str:
    if value and not _HEX_COLOR.fullmatch(value):
        msg = "A colour must be #rgb or #rrggbb."
        raise ValueError(msg)
    return value


def _severity_key(value: str) -> str:
    if value not in SEVERITY_ORDER:
        msg = f"Severity must be one of {', '.join(SEVERITY_ORDER)}."
        raise ValueError(msg)
    return value


def _font_key(value: str) -> str:
    if not _FONT_KEY.fullmatch(value):
        msg = "A font key may contain letters, digits and hyphens only."
        raise ValueError(msg)
    return value


HexColor = Annotated[str, AfterValidator(_color)]
SeverityKey = Annotated[str, AfterValidator(_severity_key)]
FontKey = Annotated[str, AfterValidator(_font_key)]


class ThemeOrigin(StrEnum):
    BUILTIN = "builtin"
    CUSTOM = "custom"


class CoverLayout(StrEnum):
    BAND = "band"
    RULE = "rule"
    FULL = "full"
    SPLIT = "split"
    MINIMAL = "minimal"


COVER_LAYOUT_LABELS: dict[str, str] = {
    CoverLayout.BAND.value: "Colour band",
    CoverLayout.RULE.value: "Rule and title",
    CoverLayout.FULL.value: "Full bleed",
    CoverLayout.SPLIT.value: "Split panel",
    CoverLayout.MINIMAL.value: "Minimal",
}


class CoverArt(StrEnum):
    NONE = "none"
    GRID = "grid"
    TOPO = "topo"
    MESH = "mesh"
    SCAN = "scan"
    RINGS = "rings"


class TableStyle(StrEnum):
    HAIRLINE = "hairline"
    ZEBRA = "zebra"
    BOXED = "boxed"
    OPEN = "open"


class FindingStyle(StrEnum):
    RAIL = "rail"
    CARD = "card"
    PLAIN = "plain"
    BANNER = "banner"


class HeadingStyle(StrEnum):
    NUMBERED = "numbered"
    RULE = "rule"
    PLAIN = "plain"
    KICKER = "kicker"


class ColorTokens(BaseModel):
    model_config = ConfigDict(extra="ignore")

    page: HexColor = "#ffffff"
    ink: HexColor = "#16181d"
    ink_soft: HexColor = "#4a4f5a"
    ink_faint: HexColor = "#82889a"
    rule: HexColor = "#e3e5ea"
    rule_strong: HexColor = "#c8ccd4"
    surface: HexColor = "#f6f7f9"
    surface_soft: HexColor = "#fafbfc"
    accent: HexColor = "#4f46e5"
    accent_soft: HexColor = "#eef0fe"
    accent_ink: HexColor = "#ffffff"
    link: HexColor = ""
    severity: dict[SeverityKey, HexColor] = Field(default_factory=dict)
    chart: list[HexColor] = Field(default_factory=list, max_length=8)


class TypeTokens(BaseModel):
    model_config = ConfigDict(extra="ignore")

    heading: FontKey = "inter"
    body: FontKey = "inter"
    mono: FontKey = "jetbrains-mono"
    base_size: float = Field(default=9.5, ge=6, le=16)
    scale: float = Field(default=1.22, ge=1.05, le=1.5)
    line_height: float = Field(default=1.55, ge=1.0, le=2.4)
    heading_weight: int = Field(default=650, ge=300, le=900)
    heading_tracking: float = Field(default=-0.01, ge=-0.08, le=0.2)
    label_tracking: float = Field(default=0.08, ge=-0.05, le=0.4)
    uppercase_labels: bool = True
    numeric_tabular: bool = True


class LayoutTokens(BaseModel):
    model_config = ConfigDict(extra="ignore")

    rule_width: float = Field(default=0.5, ge=0.2, le=2.0)
    radius: float = Field(default=3.0, ge=0, le=12)
    pill: bool = True
    block_gap: float = Field(default=1.0, ge=0.4, le=2.5)
    table: str = TableStyle.HAIRLINE.value
    finding: str = FindingStyle.RAIL.value
    heading: str = HeadingStyle.NUMBERED.value
    chart_stroke: float = Field(default=1.0, ge=0.4, le=3.0)


class CoverTokens(BaseModel):
    model_config = ConfigDict(extra="ignore")

    layout: str = CoverLayout.BAND.value
    art: str = CoverArt.NONE.value
    ink: str = "light"
    background: HexColor = ""
    accent_bar: bool = True


class ThemeTokens(BaseModel):
    """The whole look of a document, as a file a person can write."""

    model_config = ConfigDict(extra="ignore")

    key: str = Field(default="", max_length=THEME_SLUG_LENGTH)
    name: str = Field(default="", max_length=120)
    description: str = Field(default="", max_length=400)
    author: str = Field(default="", max_length=120)
    version: str = Field(default="1", max_length=20)
    color: ColorTokens = Field(default_factory=ColorTokens)
    dark: ColorTokens | None = None
    type: TypeTokens = Field(default_factory=TypeTokens)
    layout: LayoutTokens = Field(default_factory=LayoutTokens)
    cover: CoverTokens = Field(default_factory=CoverTokens)
    css: str = Field(default="", max_length=MAX_THEME_CSS)

    @field_validator("css")
    @classmethod
    def _no_markup(cls, value: str) -> str:
        if "<" in value:
            msg = "The css block may not contain <."
            raise ValueError(msg)
        return value
