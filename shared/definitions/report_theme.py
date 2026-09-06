"""A report theme is data: tokens a user can write, upload and share, never code."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

MAX_THEME_BYTES = 200_000
MAX_THEME_CSS = 60_000
THEME_SLUG_LENGTH = 48


class ThemeOrigin(StrEnum):
    BUILTIN = "builtin"
    CUSTOM = "custom"


THEME_ORIGIN_LABELS: dict[str, str] = {
    ThemeOrigin.BUILTIN.value: "Shipped themes",
    ThemeOrigin.CUSTOM.value: "Your themes",
}


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


COVER_ART_LABELS: dict[str, str] = {
    CoverArt.NONE.value: "None",
    CoverArt.GRID.value: "Grid",
    CoverArt.TOPO.value: "Contours",
    CoverArt.MESH.value: "Mesh",
    CoverArt.SCAN.value: "Scan lines",
    CoverArt.RINGS.value: "Rings",
}


class TableStyle(StrEnum):
    HAIRLINE = "hairline"
    ZEBRA = "zebra"
    BOXED = "boxed"
    OPEN = "open"


TABLE_STYLE_LABELS: dict[str, str] = {
    TableStyle.HAIRLINE.value: "Hairline",
    TableStyle.ZEBRA.value: "Zebra",
    TableStyle.BOXED.value: "Boxed",
    TableStyle.OPEN.value: "Open",
}


class FindingStyle(StrEnum):
    RAIL = "rail"
    CARD = "card"
    PLAIN = "plain"
    BANNER = "banner"


FINDING_STYLE_LABELS: dict[str, str] = {
    FindingStyle.RAIL.value: "Severity rail",
    FindingStyle.CARD.value: "Card",
    FindingStyle.PLAIN.value: "Plain",
    FindingStyle.BANNER.value: "Severity banner",
}


class HeadingStyle(StrEnum):
    NUMBERED = "numbered"
    RULE = "rule"
    PLAIN = "plain"
    KICKER = "kicker"


HEADING_STYLE_LABELS: dict[str, str] = {
    HeadingStyle.NUMBERED.value: "Numbered",
    HeadingStyle.RULE.value: "Rule above",
    HeadingStyle.PLAIN.value: "Plain",
    HeadingStyle.KICKER.value: "Kicker label",
}


class ColorTokens(BaseModel):
    model_config = ConfigDict(extra="ignore")

    page: str = "#ffffff"
    ink: str = "#16181d"
    ink_soft: str = "#4a4f5a"
    ink_faint: str = "#82889a"
    rule: str = "#e3e5ea"
    rule_strong: str = "#c8ccd4"
    surface: str = "#f6f7f9"
    surface_soft: str = "#fafbfc"
    accent: str = "#4f46e5"
    accent_soft: str = "#eef0fe"
    accent_ink: str = "#ffffff"
    link: str = ""
    severity: dict[str, str] = Field(default_factory=dict)
    chart: list[str] = Field(default_factory=list, max_length=8)


class TypeTokens(BaseModel):
    model_config = ConfigDict(extra="ignore")

    heading: str = "inter"
    body: str = "inter"
    mono: str = "jetbrains-mono"
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
    radius: float = Field(default=2.0, ge=0, le=12)
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
    background: str = ""
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
