"""One entry point: a spec and a subject in, rendered files out."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session

from reports import theme_store
from reports.analysis.engine import build_brief
from reports.base import RenderContext
from reports.data.source import ReportSource
from reports.fonts import font_faces
from reports.narrate import build_narrator
from reports.render.document import render_html
from reports.render.text import to_json, to_markdown
from reports.theme import resolve
from shared.definitions.reports import (
    FORMAT_EXTENSIONS,
    ReportFormat,
    ReportScope,
    ReportSpec,
)
from shared.logging import get_logger
from shared.models.scan import Scan
from shared.models.target import Target
from shared.services.ai.client import AIUsage
from shared.services.ai.config import load_config
from shared.utils.datetime import utc_now

logger = get_logger(__name__)

Progress = Callable[[int, str], None]


@dataclass
class RenderOutput:
    files: dict[str, bytes] = field(default_factory=dict)
    pages: int | None = None
    warnings: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)
    usage: AIUsage = field(default_factory=AIUsage)
    ai_used: bool = False
    ai_model: str = ""
    ai_provider: str = ""
    html: str = ""

    def filename(self, fmt: str, stem: str) -> str:
        return f"{stem}.{FORMAT_EXTENSIONS.get(fmt, fmt)}"


def build_context(
    session: Session,
    spec: ReportSpec,
    *,
    scan: Scan | None,
    target: Target,
    project_name: str = "",
    preview: bool = False,
    now: datetime | None = None,
) -> RenderContext:
    source = ReportSource(
        session,
        scope=spec.scope or ReportScope.SCAN.value,
        scan=scan,
        target=target,
        project_name=project_name,
    )
    brief = build_brief(source)
    cfg = load_config(session)
    narrator = build_narrator(session, cfg, spec.narrative)
    tokens = resolve(theme_store.load(session, spec.style.theme), spec.style)
    return RenderContext(
        spec=spec,
        theme=tokens,
        data=source,
        brief=brief,
        narrator=narrator,
        now=now or utc_now(),
        preview=preview,
    )


def generate(
    session: Session,
    spec: ReportSpec,
    *,
    scan: Scan | None,
    target: Target,
    project_name: str = "",
    preview: bool = False,
    progress: Progress | None = None,
) -> RenderOutput:
    def step(percent: int, label: str) -> None:
        if progress:
            progress(percent, label)

    step(10, "Reading the scan")
    ctx = build_context(
        session,
        spec,
        scan=scan,
        target=target,
        project_name=project_name,
        preview=preview,
    )

    step(35, "Writing the narrative")
    document = render_html(ctx)

    out = RenderOutput(
        warnings=document.warnings,
        html=document.html,
        ai_used=getattr(ctx.narrator, "used_model", False),
        usage=ctx.narrator.usage,
    )
    cfg = load_config(session)
    if cfg is not None:
        out.ai_provider = cfg.provider
        out.ai_model = cfg.model

    formats = spec.formats or [ReportFormat.PDF.value]
    if ReportFormat.HTML.value in formats:
        used = frozenset(
            {ctx.theme.type.heading, ctx.theme.type.body, ctx.theme.type.mono}
        )
        embedded = font_faces(session, embed=True, only=used)
        standalone = (
            document.html.replace(document.faces, embedded)
            if document.faces
            else document.html
        )
        out.files[ReportFormat.HTML.value] = standalone.encode("utf-8")
    if ReportFormat.MARKDOWN.value in formats:
        out.files[ReportFormat.MARKDOWN.value] = to_markdown(ctx).encode("utf-8")
    if ReportFormat.JSON.value in formats:
        out.files[ReportFormat.JSON.value] = to_json(ctx).encode("utf-8")

    if ReportFormat.PDF.value in formats:
        step(70, "Laying out the pages")
        from reports.render.pdf import to_pdf  # noqa: PLC0415

        result = to_pdf(document.html, base_url=str(_base_url()))
        out.files[ReportFormat.PDF.value] = result.data
        out.pages = result.pages
        out.warnings.extend(w for w in result.warnings if w not in out.warnings)

    out.stats = {
        "sections": len(document.rendered),
        "skipped": document.skipped,
        "findings": len(ctx.data.findings),
        "issues": len(ctx.brief.risks),
        "hosts": ctx.data.count_of("web_assets"),
        "score": ctx.brief.posture.score,
        "grade": ctx.brief.posture.grade,
        "paths": len(ctx.brief.paths),
    }
    step(95, "Finishing")
    return out


def _base_url() -> str:
    from pathlib import Path  # noqa: PLC0415

    return (Path(__file__).resolve().parent / "assets").as_uri() + "/"
