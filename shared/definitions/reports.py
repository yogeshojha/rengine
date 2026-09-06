"""The report vocabulary: formats, scopes, page setup and the customisation surface."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_SECTIONS = 60
MAX_CUSTOM_BLOCKS = 20
MAX_TITLE_LENGTH = 200
MAX_TEXT_BLOCK = 20_000
MAX_LOGO_BYTES = 512_000
MAX_REPORT_ROWS = 5_000
MAX_EVIDENCE_CHARS = 4_000
MAX_SCREENSHOTS = 60
# a 500 KB PNG can still decode to a 64M pixel canvas, so the ceiling is on pixels, not bytes
MAX_IMAGE_PIXELS = 30_000_000
REPORT_ROOT = "/app/reports-out"
RETENTION_DAYS = 90


class ReportFormat(StrEnum):
    PDF = "pdf"
    HTML = "html"
    MARKDOWN = "markdown"
    JSON = "json"


REPORT_FORMATS: tuple[str, ...] = tuple(f.value for f in ReportFormat)

FORMAT_LABELS: dict[str, str] = {
    ReportFormat.PDF.value: "PDF",
    ReportFormat.HTML.value: "HTML",
    ReportFormat.MARKDOWN.value: "Markdown",
    ReportFormat.JSON.value: "JSON",
}

FORMAT_MEDIA_TYPES: dict[str, str] = {
    ReportFormat.PDF.value: "application/pdf",
    ReportFormat.HTML.value: "text/html",
    ReportFormat.MARKDOWN.value: "text/markdown",
    ReportFormat.JSON.value: "application/json",
}

FORMAT_EXTENSIONS: dict[str, str] = {
    ReportFormat.PDF.value: "pdf",
    ReportFormat.HTML.value: "html",
    ReportFormat.MARKDOWN.value: "md",
    ReportFormat.JSON.value: "json",
}


class ReportStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


REPORT_STATUS_LABELS: dict[str, str] = {
    ReportStatus.QUEUED.value: "Queued",
    ReportStatus.RUNNING.value: "Generating",
    ReportStatus.COMPLETED.value: "Ready",
    ReportStatus.FAILED.value: "Failed",
}

TERMINAL_STATUSES: tuple[str, ...] = (
    ReportStatus.COMPLETED.value,
    ReportStatus.FAILED.value,
)


class ReportScope(StrEnum):
    SCAN = "scan"
    TARGET = "target"


REPORT_SCOPES: tuple[str, ...] = tuple(s.value for s in ReportScope)

SCOPE_LABELS: dict[str, str] = {
    ReportScope.SCAN.value: "One scan",
    ReportScope.TARGET.value: "A target",
}

SCOPE_HELP: dict[str, str] = {
    ReportScope.SCAN.value: "Everything a single run observed, as it observed it.",
    ReportScope.TARGET.value: "The target's current surface, taken from the most recent run that covered each dimension.",
}


class SectionGroup(StrEnum):
    FRONT_MATTER = "front_matter"
    SUMMARY = "summary"
    FINDINGS = "findings"
    SURFACE = "surface"
    INTELLIGENCE = "intelligence"
    APPENDIX = "appendix"


SECTION_GROUP_ORDER: tuple[str, ...] = tuple(g.value for g in SectionGroup)

SECTION_GROUP_LABELS: dict[str, str] = {
    SectionGroup.FRONT_MATTER.value: "Front matter",
    SectionGroup.SUMMARY.value: "Summary",
    SectionGroup.FINDINGS.value: "Findings",
    SectionGroup.SURFACE.value: "Attack surface",
    SectionGroup.INTELLIGENCE.value: "Intelligence",
    SectionGroup.APPENDIX.value: "Appendices",
}


class SectionRole(StrEnum):
    """Content is what a reader asked for; furniture is the document around it."""

    CONTENT = "content"
    FURNITURE = "furniture"


SECTION_ROLES: tuple[str, ...] = tuple(r.value for r in SectionRole)


class Audience(StrEnum):
    EXECUTIVE = "executive"
    TECHNICAL = "technical"
    MIXED = "mixed"


AUDIENCE_LABELS: dict[str, str] = {
    Audience.EXECUTIVE.value: "Executive",
    Audience.TECHNICAL.value: "Technical",
    Audience.MIXED.value: "Mixed",
}

AUDIENCE_HELP: dict[str, str] = {
    Audience.EXECUTIVE.value: "Business impact and decisions. No tool names or payloads.",
    Audience.TECHNICAL.value: "Reproduction detail, evidence and exact remediation steps.",
    Audience.MIXED.value: "An executive opening followed by full technical detail.",
}


class Depth(StrEnum):
    BRIEF = "brief"
    STANDARD = "standard"
    DETAILED = "detailed"


DEPTH_LABELS: dict[str, str] = {
    Depth.BRIEF.value: "Brief",
    Depth.STANDARD.value: "Standard",
    Depth.DETAILED.value: "Detailed",
}


class PageSize(StrEnum):
    A4 = "a4"
    LETTER = "letter"
    LEGAL = "legal"


PAGE_SIZE_LABELS: dict[str, str] = {
    PageSize.A4.value: "A4",
    PageSize.LETTER.value: "US Letter",
    PageSize.LEGAL.value: "US Legal",
}

PAGE_SIZE_CSS: dict[str, str] = {
    PageSize.A4.value: "A4",
    PageSize.LETTER.value: "Letter",
    PageSize.LEGAL.value: "Legal",
}

# printable width in mm, used to size charts and decide table column budgets
PAGE_WIDTH_MM: dict[str, float] = {
    PageSize.A4.value: 210.0,
    PageSize.LETTER.value: 215.9,
    PageSize.LEGAL.value: 215.9,
}


class Orientation(StrEnum):
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


ORIENTATION_LABELS: dict[str, str] = {
    Orientation.PORTRAIT.value: "Portrait",
    Orientation.LANDSCAPE.value: "Landscape",
}


class Density(StrEnum):
    COMPACT = "compact"
    NORMAL = "normal"
    RELAXED = "relaxed"


DENSITY_LABELS: dict[str, str] = {
    Density.COMPACT.value: "Compact",
    Density.NORMAL.value: "Normal",
    Density.RELAXED.value: "Relaxed",
}

DENSITY_SCALE: dict[str, float] = {
    Density.COMPACT.value: 0.85,
    Density.NORMAL.value: 1.0,
    Density.RELAXED.value: 1.18,
}


class Classification(StrEnum):
    NONE = ""
    PUBLIC = "Public"
    INTERNAL = "Internal"
    CONFIDENTIAL = "Confidential"
    RESTRICTED = "Restricted"


CLASSIFICATIONS: tuple[str, ...] = tuple(c.value for c in Classification)


@dataclass(frozen=True)
class FontFamily:
    key: str
    label: str
    stack: str
    role: str
    note: str = ""


# families vendored under reports/assets/fonts; the stack is what the CSS asks for
FONT_FAMILIES: tuple[FontFamily, ...] = (
    FontFamily("inter", "Inter", "Inter", "sans", "Neutral UI sans."),
    FontFamily(
        "space-grotesk", "Space Grotesk", "Space Grotesk", "sans", "Display sans."
    ),
    FontFamily("ibm-plex-sans", "IBM Plex Sans", "IBM Plex Sans", "sans", "Technical."),
    FontFamily(
        "source-serif", "Source Serif 4", "Source Serif 4", "serif", "Document serif."
    ),
    FontFamily(
        "jetbrains-mono",
        "JetBrains Mono",
        "JetBrains Mono",
        "mono",
        "Code and evidence.",
    ),
    FontFamily("ibm-plex-mono", "IBM Plex Mono", "IBM Plex Mono", "mono", "Code."),
)

FONT_BY_KEY: dict[str, FontFamily] = {f.key: f for f in FONT_FAMILIES}
SANS_FONTS: tuple[str, ...] = tuple(f.key for f in FONT_FAMILIES if f.role == "sans")
SERIF_FONTS: tuple[str, ...] = tuple(f.key for f in FONT_FAMILIES if f.role == "serif")
MONO_FONTS: tuple[str, ...] = tuple(f.key for f in FONT_FAMILIES if f.role == "mono")


@dataclass(frozen=True)
class SlotToken:
    token: str
    label: str


# substituted into the running header and footer slots
SLOT_TOKENS: tuple[SlotToken, ...] = (
    SlotToken("{title}", "Report title"),
    SlotToken("{subtitle}", "Subtitle"),
    SlotToken("{target}", "Target"),
    SlotToken("{client}", "Client name"),
    SlotToken("{company}", "Your company"),
    SlotToken("{classification}", "Classification"),
    SlotToken("{date}", "Report date"),
    SlotToken("{scan_date}", "Scan date"),
    SlotToken("{document_id}", "Document ID"),
    SlotToken("{version}", "Version"),
    SlotToken("{section}", "Current section"),
    SlotToken("{page}", "Page number"),
    SlotToken("{pages}", "Total pages"),
)

SLOT_TOKEN_VALUES: tuple[str, ...] = tuple(t.token for t in SLOT_TOKENS)

DEFAULT_HEADER_LEFT = "{section}"
DEFAULT_HEADER_RIGHT = "{classification}"
DEFAULT_FOOTER_LEFT = "{title}"
DEFAULT_FOOTER_CENTER = ""
DEFAULT_FOOTER_RIGHT = "{page} / {pages}"

DEFAULT_THEME = "midnight"

# an uploaded image is embedded, never referenced, so the renderer can never be made to fetch
ALLOWED_IMAGE_TYPES: frozenset[str] = frozenset(
    {"image/png", "image/jpeg", "image/svg+xml", "image/webp", "image/gif"}
)
_DATA_IMAGE = re.compile(r"^data:(image/[a-z0-9.+-]+);base64,[A-Za-z0-9+/=\s]+$", re.I)


def validate_embedded_image(value: str, field: str) -> str:
    """An image must be embedded data of a known type. A URL is refused, not fetched."""
    text = (value or "").strip()
    if not text:
        return ""
    match = _DATA_IMAGE.match(text)
    if match is None:
        msg = (
            f"{field} must be an uploaded image. "
            "A link is not accepted, because a report never fetches from the network."
        )
        raise ValueError(msg)
    if match.group(1).lower() not in ALLOWED_IMAGE_TYPES:
        msg = f"{field} must be a PNG, JPEG, SVG, WebP or GIF."
        raise ValueError(msg)
    if len(text) > MAX_LOGO_BYTES:
        msg = f"{field} is larger than the {MAX_LOGO_BYTES // 1024} KB limit."
        raise ValueError(msg)
    return text


# Severity is a reserved ramp, not a theme decision: it means the same thing in every
# document. Lightness carries the rank so it survives deuteranopia, and each level is
# always printed beside its own label. Validated all-pairs on white paper.
DEFAULT_SEVERITY_COLORS: dict[str, str] = {
    "critical": "#d02f43",
    "high": "#f07c21",
    "medium": "#e7c65c",
    "low": "#3c8edf",
    "info": "#a8bacb",
    "unknown": "#a8bacb",
}

# the same ramp restepped for dark paper
DARK_SEVERITY_COLORS: dict[str, str] = {
    "critical": "#ed566f",
    "high": "#f3963e",
    "medium": "#efda79",
    "low": "#69bbff",
    "info": "#858f9a",
    "unknown": "#858f9a",
}

# a categorical scale that clears the CVD and contrast gates on both papers
DEFAULT_CHART_PALETTE: tuple[str, ...] = (
    "#2a78d6",
    "#eb6834",
    "#1baf7a",
    "#eda100",
    "#e87ba4",
)
DARK_CHART_PALETTE: tuple[str, ...] = (
    "#3987e5",
    "#d95926",
    "#199e70",
    "#c98500",
    "#d55181",
)


class ReportStyle(BaseModel):
    """Everything about how the document looks. Empty means the theme decides."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    theme: str = Field(default=DEFAULT_THEME, max_length=40)
    page_size: str = Field(default=PageSize.A4.value, max_length=10)
    orientation: str = Field(default=Orientation.PORTRAIT.value, max_length=10)
    margin_top: float = Field(default=26.0, ge=5, le=60)
    margin_right: float = Field(default=24.0, ge=5, le=60)
    margin_bottom: float = Field(default=23.0, ge=5, le=60)
    margin_left: float = Field(default=24.0, ge=5, le=60)
    density: str = Field(default=Density.NORMAL.value, max_length=10)
    base_font_size: float = Field(default=10.5, ge=6, le=16)
    line_height: float = Field(default=1.6, ge=1.0, le=2.4)
    heading_font: str = Field(default="", max_length=40)
    body_font: str = Field(default="", max_length=40)
    mono_font: str = Field(default="", max_length=40)
    accent: str = Field(default="", max_length=9)
    accent_soft: str = Field(default="", max_length=9)
    severity_colors: dict[str, str] = Field(default_factory=dict)
    chart_palette: list[str] = Field(default_factory=list, max_length=8)
    mono_safe: bool = False
    table_zebra: bool = True
    section_numbering: bool = True
    chapter_breaks: bool = True
    figure_numbering: bool = True
    page_numbers: bool = True
    show_header: bool = True
    show_footer: bool = True
    header_left: str = Field(default=DEFAULT_HEADER_LEFT, max_length=120)
    header_center: str = Field(default="", max_length=120)
    header_right: str = Field(default=DEFAULT_HEADER_RIGHT, max_length=120)
    footer_left: str = Field(default=DEFAULT_FOOTER_LEFT, max_length=120)
    footer_center: str = Field(default=DEFAULT_FOOTER_CENTER, max_length=120)
    footer_right: str = Field(default=DEFAULT_FOOTER_RIGHT, max_length=120)
    cover_layout: str = Field(default="", max_length=40)
    cover_image: str = Field(default="", max_length=MAX_LOGO_BYTES)
    watermark_text: str = Field(default="", max_length=40)
    watermark_opacity: float = Field(default=0.05, ge=0.01, le=0.4)
    link_urls: bool = True
    justify: bool = True
    hyphenate: bool = True

    @field_validator("cover_image")
    @classmethod
    def _cover_is_embedded(cls, value: str) -> str:
        return validate_embedded_image(value, "The cover image")


class Revision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = Field(default="", max_length=20)
    date: str = Field(default="", max_length=40)
    author: str = Field(default="", max_length=120)
    note: str = Field(default="", max_length=500)


class ReportBranding(BaseModel):
    """Who the document is from, who it is for, and what may be done with it."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    company_name: str = Field(default="", max_length=160)
    company_logo: str = Field(default="", max_length=MAX_LOGO_BYTES)
    client_name: str = Field(default="", max_length=160)
    prepared_for: str = Field(default="", max_length=200)
    prepared_by: str = Field(default="", max_length=200)
    author: str = Field(default="", max_length=160)
    contact_email: str = Field(default="", max_length=200)
    contact_url: str = Field(default="", max_length=300)
    classification: str = Field(default="", max_length=40)
    document_id: str = Field(default="", max_length=60)
    version: str = Field(default="", max_length=20)
    distribution: list[str] = Field(default_factory=list, max_length=20)
    revisions: list[Revision] = Field(default_factory=list, max_length=20)
    confidentiality_statement: str = Field(default="", max_length=2000)
    disclaimer: str = Field(default="", max_length=2000)

    @field_validator("company_logo")
    @classmethod
    def _logo_is_embedded(cls, value: str) -> str:
        return validate_embedded_image(value, "The logo")


class NarrativeOptions(BaseModel):
    """How the prose is written, and whether a model writes any of it."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    ai_enabled: bool = False
    audience: str = Field(default=Audience.MIXED.value, max_length=20)
    depth: str = Field(default=Depth.STANDARD.value, max_length=20)
    explain_findings: bool = False
    max_explained_issues: int = Field(default=12, ge=1, le=40)
    model: str = Field(default="", max_length=80)
    disclose_ai: bool = True
    house_style: str = Field(default="", max_length=1000)


class SectionEntry(BaseModel):
    """One row of the document outline."""

    model_config = ConfigDict(extra="forbid")

    section: str = Field(max_length=60)
    enabled: bool = True
    title: str = Field(default="", max_length=MAX_TITLE_LENGTH)
    config: dict = Field(default_factory=dict)


class ReportSpec(BaseModel):
    """The resolved document: what to say, about what, and how it looks."""

    model_config = ConfigDict(extra="ignore")

    title: str = Field(default="", max_length=MAX_TITLE_LENGTH)
    subtitle: str = Field(default="", max_length=MAX_TITLE_LENGTH)
    scope: str = Field(default=ReportScope.SCAN.value, max_length=16)
    sections: list[SectionEntry] = Field(default_factory=list, max_length=MAX_SECTIONS)
    style: ReportStyle = Field(default_factory=ReportStyle)
    branding: ReportBranding = Field(default_factory=ReportBranding)
    narrative: NarrativeOptions = Field(default_factory=NarrativeOptions)
    formats: list[str] = Field(default_factory=lambda: [ReportFormat.PDF.value])


def coerce_format(value: str | None) -> str:
    key = (value or "").strip().lower()
    return key if key in FORMAT_LABELS else ReportFormat.PDF.value


def coerce_scope(value: str | None) -> str:
    key = (value or "").strip().lower()
    return key if key in REPORT_SCOPES else ReportScope.SCAN.value
