import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField
from sqlalchemy import Column, Text
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel, UniqueConstraint

from shared.definitions.report_fonts import (
    MAX_FACES,
    MAX_FAMILY_NAME,
    FontOrigin,
    FontRole,
)
from shared.definitions.report_theme import ThemeOrigin, ThemeTokens
from shared.definitions.reports import (
    MAX_SECTIONS,
    MAX_TITLE_LENGTH,
    NarrativeOptions,
    ReportBranding,
    ReportFormat,
    ReportScope,
    ReportSpec,
    ReportStatus,
    ReportStyle,
    SectionEntry,
)
from shared.utils.datetime import utc_now


def _json_list() -> Field:
    return Field(default_factory=list, sa_column=Column(JSON, nullable=False))


def _json_dict() -> Field:
    return Field(default_factory=dict, sa_column=Column(JSON, nullable=False))


class ReportTemplate(SQLModel, table=True):
    """A saved document: which sections run, in what order, and how it looks."""

    __tablename__ = "report_templates"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    project_id: uuid.UUID | None = Field(default=None, index=True)
    slug: str = Field(max_length=64, index=True)
    name: str = Field(max_length=200)
    description: str = Field(default="", max_length=1000)
    title: str = Field(default="", max_length=MAX_TITLE_LENGTH)
    subtitle: str = Field(default="", max_length=MAX_TITLE_LENGTH)
    preset: str = Field(default="", max_length=40)
    tags: list = _json_list()
    scope: str = Field(default=ReportScope.SCAN.value, max_length=16, index=True)
    sections: list = _json_list()
    theme: str = Field(default="", max_length=64)
    style: dict = _json_dict()
    branding: dict = _json_dict()
    narrative: dict = _json_dict()
    formats: list = _json_list()
    is_builtin: bool = Field(default=False, index=True)
    is_default: bool = Field(default=False)
    used_count: int = Field(default=0)
    last_used_at: datetime | None = Field(default=None)
    created_by: uuid.UUID | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Report(SQLModel, table=True):
    """One generated document. The spec is stored so a report can always be explained."""

    __tablename__ = "reports"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)
    template_id: uuid.UUID | None = Field(default=None, index=True)
    template_name: str = Field(default="", max_length=200)
    scope: str = Field(default=ReportScope.SCAN.value, max_length=16, index=True)
    scan_id: uuid.UUID | None = Field(default=None, index=True)
    target_id: uuid.UUID | None = Field(default=None, index=True)
    subject: str = Field(default="", max_length=500)
    title: str = Field(default="", max_length=MAX_TITLE_LENGTH)
    spec: dict = _json_dict()

    status: str = Field(default=ReportStatus.QUEUED.value, max_length=16, index=True)
    progress: int = Field(default=0)
    step: str = Field(default="", max_length=120)
    error: str | None = Field(default=None, max_length=2000)
    task_id: str | None = Field(default=None, max_length=120)

    files: list = _json_list()
    page_count: int | None = Field(default=None)
    stats: dict = _json_dict()

    ai_used: bool = Field(default=False)
    ai_provider: str | None = Field(default=None, max_length=32)
    ai_model: str | None = Field(default=None, max_length=80)
    ai_calls: int = Field(default=0)
    ai_input_tokens: int = Field(default=0)
    ai_output_tokens: int = Field(default=0)
    ai_cached_calls: int = Field(default=0)

    duration_seconds: float | None = Field(default=None)
    created_by: uuid.UUID | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now, index=True)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    expires_at: datetime | None = Field(default=None)


class ReportTheme(SQLModel, table=True):
    """A look, stored as tokens. Shipped themes are indexed from disk; the rest are uploads."""

    __tablename__ = "report_themes"
    __table_args__ = (UniqueConstraint("slug", name="uq_report_theme_slug"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    slug: str = Field(max_length=64, index=True)
    name: str = Field(max_length=120)
    description: str = Field(default="", max_length=400)
    author: str = Field(default="", max_length=120)
    version: str = Field(default="1", max_length=20)
    origin: str = Field(default=ThemeOrigin.CUSTOM.value, max_length=16, index=True)
    tokens: dict = _json_dict()
    source: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    uploaded_by: uuid.UUID | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ReportFont(SQLModel, table=True):
    """One typeface family. Its faces live on the report-fonts volume, named by us."""

    __tablename__ = "report_fonts"
    __table_args__ = (UniqueConstraint("slug", name="uq_report_font_slug"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    slug: str = Field(max_length=64, index=True)
    name: str = Field(max_length=MAX_FAMILY_NAME)
    role: str = Field(default=FontRole.SANS.value, max_length=8, index=True)
    origin: str = Field(default=FontOrigin.CUSTOM.value, max_length=16, index=True)
    note: str = Field(default="", max_length=300)
    faces: list = _json_list()
    bytes: int = Field(default=0)
    uploaded_by: uuid.UUID | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class FontFace(BaseModel):
    weight: int = 400
    italic: bool = False
    filename: str = ""
    format: str = "woff2"
    bytes: int = 0


class FontFaceUpload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str = PydanticField(default="", max_length=200)
    content: str = PydanticField(max_length=3_000_000)
    weight: int = PydanticField(default=400, ge=100, le=900)
    italic: bool = False


class ReportFontUpload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = PydanticField(max_length=MAX_FAMILY_NAME)
    role: str = PydanticField(default=FontRole.SANS.value, max_length=8)
    note: str = PydanticField(default="", max_length=300)
    faces: list[FontFaceUpload] = PydanticField(min_length=1, max_length=MAX_FACES)


class ReportFontRead(BaseModel):
    id: uuid.UUID | None = None
    slug: str
    name: str
    role: str
    origin: str
    note: str = ""
    faces: list[FontFace] = PydanticField(default_factory=list)
    weights: list[int] = PydanticField(default_factory=list)
    bytes: int = 0
    created_at: datetime | None = None


class ReportDefaults(BaseModel):
    """Instance-wide starting point, so a logo and a classification are set once."""

    model_config = ConfigDict(extra="ignore")

    branding: ReportBranding = PydanticField(default_factory=ReportBranding)
    theme: str = PydanticField(default="", max_length=64)
    footer_note: str = PydanticField(default="", max_length=300)


class ReportFile(BaseModel):
    format: str
    filename: str
    bytes: int
    pages: int | None = None


class ReportTemplateCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = PydanticField(max_length=200)
    description: str = PydanticField(default="", max_length=1000)
    title: str = PydanticField(default="", max_length=MAX_TITLE_LENGTH)
    subtitle: str = PydanticField(default="", max_length=MAX_TITLE_LENGTH)
    scope: str = PydanticField(default=ReportScope.SCAN.value, max_length=16)
    sections: list[SectionEntry] = PydanticField(
        default_factory=list, max_length=MAX_SECTIONS
    )
    theme: str = PydanticField(default="", max_length=64)
    style: ReportStyle = PydanticField(default_factory=ReportStyle)
    branding: ReportBranding = PydanticField(default_factory=ReportBranding)
    narrative: NarrativeOptions = PydanticField(default_factory=NarrativeOptions)
    formats: list[str] = PydanticField(
        default_factory=lambda: [ReportFormat.PDF.value], max_length=4
    )
    clone_of: uuid.UUID | None = None


class ReportTemplateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = PydanticField(default=None, max_length=200)
    description: str | None = PydanticField(default=None, max_length=1000)
    title: str | None = PydanticField(default=None, max_length=MAX_TITLE_LENGTH)
    subtitle: str | None = PydanticField(default=None, max_length=MAX_TITLE_LENGTH)
    scope: str | None = PydanticField(default=None, max_length=16)
    sections: list[SectionEntry] | None = PydanticField(
        default=None, max_length=MAX_SECTIONS
    )
    theme: str | None = PydanticField(default=None, max_length=64)
    style: ReportStyle | None = None
    branding: ReportBranding | None = None
    narrative: NarrativeOptions | None = None
    formats: list[str] | None = PydanticField(default=None, max_length=4)
    is_default: bool | None = None


class ReportTemplateRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID | None
    slug: str
    name: str
    description: str
    title: str = ""
    subtitle: str = ""
    preset: str = ""
    tags: list[str] = PydanticField(default_factory=list)
    scope: str
    sections: list[SectionEntry]
    theme: str
    style: ReportStyle
    branding: ReportBranding
    narrative: NarrativeOptions
    formats: list[str]
    is_builtin: bool
    is_default: bool
    used_count: int
    last_used_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ReportCreate(BaseModel):
    """Ask for a document. Everything but the subject may come from the template."""

    model_config = ConfigDict(extra="forbid")

    template_id: uuid.UUID | None = None
    scope: str | None = PydanticField(default=None, max_length=16)
    scan_id: uuid.UUID | None = None
    target_id: uuid.UUID | None = None
    title: str = PydanticField(default="", max_length=MAX_TITLE_LENGTH)
    subtitle: str = PydanticField(default="", max_length=MAX_TITLE_LENGTH)
    sections: list[SectionEntry] | None = PydanticField(
        default=None, max_length=MAX_SECTIONS
    )
    theme: str | None = PydanticField(default=None, max_length=64)
    style: ReportStyle | None = None
    branding: ReportBranding | None = None
    narrative: NarrativeOptions | None = None
    formats: list[str] | None = PydanticField(default=None, max_length=4)
    preview: bool = False


class ReportRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    template_id: uuid.UUID | None
    template_name: str
    scope: str
    scan_id: uuid.UUID | None
    target_id: uuid.UUID | None
    subject: str
    title: str
    status: str
    progress: int
    step: str
    error: str | None
    files: list[ReportFile] = PydanticField(default_factory=list)
    page_count: int | None
    stats: dict = PydanticField(default_factory=dict)
    theme: str = ""
    formats: list[str] = PydanticField(default_factory=list)
    ai_used: bool
    ai_model: str | None
    ai_calls: int
    ai_input_tokens: int
    ai_output_tokens: int
    ai_cached_calls: int
    duration_seconds: float | None
    created_by: uuid.UUID | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    expires_at: datetime | None


class ReportThemeRead(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    description: str
    author: str
    version: str
    origin: str
    tokens: ThemeTokens
    created_at: datetime
    updated_at: datetime


class ReportThemeUpload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str = PydanticField(default="", max_length=200)
    content: str = PydanticField(max_length=200_000)


class ReportThemeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = PydanticField(default=None, max_length=120)
    description: str | None = PydanticField(default=None, max_length=400)
    content: str | None = PydanticField(default=None, max_length=200_000)


class SectionField(BaseModel):
    """One control the builder renders for a section."""

    name: str
    label: str
    help: str = ""
    type: str = "string"
    default: object | None = None
    options: list[dict] = PydanticField(default_factory=list)
    minimum: float | None = None
    maximum: float | None = None
    widget: str = ""
    depends_on: str = ""


class SectionCatalogEntry(BaseModel):
    name: str
    title: str
    description: str
    group: str
    requires: list[str] = PydanticField(default_factory=list)
    repeatable: bool = False
    default_enabled: bool = True
    always_available: bool = True
    fields: list[SectionField] = PydanticField(default_factory=list)
    defaults: dict = PydanticField(default_factory=dict)


class ThemeSummary(BaseModel):
    slug: str
    name: str
    description: str
    author: str = ""
    origin: str = ThemeOrigin.BUILTIN.value
    accent: str = ""
    page: str = ""
    ink: str = ""
    cover_layout: str = ""
    heading_font: str = ""
    body_font: str = ""
    severity: dict[str, str] = PydanticField(default_factory=dict)
    chart: list[str] = PydanticField(default_factory=list)


class FrameworkSummary(BaseModel):
    key: str
    name: str
    version: str
    description: str
    url: str
    scope_note: str
    controls: list[dict] = PydanticField(default_factory=list)


class ReportCatalog(BaseModel):
    """Everything the builder needs to render itself."""

    sections: list[SectionCatalogEntry] = PydanticField(default_factory=list)
    groups: list[dict] = PydanticField(default_factory=list)
    themes: list[ThemeSummary] = PydanticField(default_factory=list)
    presets: list[dict] = PydanticField(default_factory=list)
    fonts: list[ReportFontRead] = PydanticField(default_factory=list)
    font_roles: list[dict] = PydanticField(default_factory=list)
    page_sizes: list[dict] = PydanticField(default_factory=list)
    formats: list[dict] = PydanticField(default_factory=list)
    scopes: list[dict] = PydanticField(default_factory=list)
    slot_tokens: list[dict] = PydanticField(default_factory=list)
    frameworks: list[FrameworkSummary] = PydanticField(default_factory=list)
    cover_layouts: list[dict] = PydanticField(default_factory=list)
    cover_art: list[dict] = PydanticField(default_factory=list)
    table_styles: list[dict] = PydanticField(default_factory=list)
    finding_styles: list[dict] = PydanticField(default_factory=list)
    heading_styles: list[dict] = PydanticField(default_factory=list)
    audiences: list[dict] = PydanticField(default_factory=list)
    depths: list[dict] = PydanticField(default_factory=list)
    densities: list[dict] = PydanticField(default_factory=list)
    ai_available: bool = False
    ai_model: str = ""


class ReportEstimate(BaseModel):
    """What a run will cost before it is started."""

    sections: int = 0
    findings: int = 0
    assets: int = 0
    pages_estimated: int = 0
    ai_calls: int = 0
    ai_input_tokens: int = 0
    ai_output_tokens: int = 0
    ai_cost_usd: float = 0.0
    ai_cached: int = 0
    warnings: list[str] = PydanticField(default_factory=list)


ReportSpecModel = ReportSpec
