"""Run the sections, number them, build the contents list, emit the document."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from reports.base import RenderContext, Section
from reports.fonts import families, font_faces
from reports.registry import SectionSpec
from reports.registry import section as lookup_section
from reports.render.css import stylesheet
from reports.render.env import environment
from shared.definitions.report_theme import HeadingStyle
from shared.logging import get_logger

logger = get_logger(__name__)

_SLUG_RE = re.compile(r"[^a-z0-9]+")
_TOC_SECTION = "contents"


@dataclass
class TocEntry:
    title: str
    anchor: str
    number: str = ""
    level: int = 1


@dataclass
class RenderedDocument:
    html: str
    faces: str = ""
    entries: list[TocEntry] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    rendered: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def slug(value: str) -> str:
    return _SLUG_RE.sub("-", (value or "").lower()).strip("-") or "section"


def _wrap(
    env,
    ctx: RenderContext,
    spec: SectionSpec,
    body: str,
    *,
    title: str,
    anchor: str,
    number: str,
    kicker: str,
    lede: str,
) -> str:
    heading = ctx.theme.layout.heading
    if heading == HeadingStyle.NUMBERED.value and not ctx.style.section_numbering:
        heading = HeadingStyle.PLAIN.value
    return env.get_template("section.html").render(
        body=body,
        title=title,
        anchor=anchor,
        number=number if heading == HeadingStyle.NUMBERED.value else "",
        kicker=kicker if heading == HeadingStyle.KICKER.value else "",
        lede=lede,
        heading_style=heading,
        flow=spec.page_break == "flow",
    )


def _build_one(
    ctx: RenderContext, spec: SectionSpec, entry, index: int, doc: RenderedDocument
):
    """Returns (html, title, anchor) or None when the section has nothing to say."""
    instance: Section = spec.instance()
    if not instance.available(ctx):
        doc.skipped.append(spec.name)
        return None
    try:
        config = spec.config(entry.config)
        payload = instance.build(ctx, config)
    except Exception as exc:
        logger.warning("section failed", section=spec.name, error=str(exc)[:300])
        doc.warnings.append(f"{spec.title} could not be built: {exc}")
        return None
    if payload is None:
        doc.skipped.append(spec.name)
        return None
    title = (entry.title or payload.pop("title", "") or spec.title).strip()
    return payload, config, title, f"s{index}-{slug(spec.name)}"


def _fill_contents(
    env, ctx: RenderContext, doc: RenderedDocument, blocks: list[str], slots: list[int]
) -> None:
    spec = lookup_section(_TOC_SECTION)
    if spec is None:
        return
    for slot in slots:
        payload = spec.instance().build(ctx, spec.config({})) or {}
        blocks[slot] = env.get_template(spec.section_cls.template_name()).render(
            ctx=ctx, entries=doc.entries, **payload
        )
        doc.rendered.append(spec.name)


def render_html(ctx: RenderContext) -> RenderedDocument:
    env = environment()
    doc = RenderedDocument(html="")
    blocks: list[str] = []
    toc_slots: list[int] = []
    counter = 0

    for index, entry in enumerate(ctx.spec.sections):
        if not entry.enabled:
            continue
        spec = lookup_section(entry.section)
        if spec is None:
            doc.warnings.append(f"Unknown section '{entry.section}'.")
            continue

        instance: Section = spec.instance()
        if not instance.available(ctx):
            doc.skipped.append(spec.name)
            continue

        try:
            config = spec.config(entry.config)
            payload = instance.build(ctx, config)
        except Exception as exc:
            logger.warning("section failed", section=spec.name, error=str(exc)[:300])
            doc.warnings.append(f"{spec.title} could not be built: {exc}")
            continue

        if payload is None:
            doc.skipped.append(spec.name)
            continue

        title = (entry.title or payload.pop("title", "") or spec.title).strip()
        anchor = f"s{index}-{slug(spec.name)}"
        number = ""
        if spec.in_toc:
            counter += 1
            number = str(counter)
            doc.entries.append(TocEntry(title=title, anchor=anchor, number=number))
            for sub_title, sub_anchor in payload.pop("toc_subs", []) or []:
                doc.entries.append(
                    TocEntry(title=sub_title, anchor=sub_anchor, level=2)
                )

        if spec.name == _TOC_SECTION:
            blocks.append("")
            toc_slots.append(len(blocks) - 1)
            continue

        bare = bool(payload.pop("bare", False))
        kicker = payload.pop("kicker", "") or spec.group.replace("_", " ")
        lede = payload.pop("lede", "")
        body = env.get_template(spec.section_cls.template_name()).render(
            ctx=ctx, cfg=config, **payload
        )
        blocks.append(
            body
            if bare
            else _wrap(
                env,
                ctx,
                spec,
                body,
                title=title,
                anchor=anchor,
                number=number,
                kicker=kicker,
                lede=lede,
            )
        )
        doc.rendered.append(spec.name)

    _fill_contents(env, ctx, doc, blocks, toc_slots)

    doc.warnings.extend(ctx.warnings)
    doc.faces = font_faces(ctx.data.session)
    doc.html = env.get_template("document.html").render(
        spec=ctx.spec,
        blocks=blocks,
        stylesheet=stylesheet(
            ctx.theme,
            ctx.style,
            slot_values(ctx),
            faces=doc.faces,
            families={f.slug: f.name for f in families(ctx.data.session)},
        ),
    )
    return doc


def slot_values(ctx: RenderContext) -> dict[str, str]:
    branding = ctx.branding
    return {
        "title": ctx.spec.title,
        "subtitle": ctx.spec.subtitle,
        "target": ctx.data.subject,
        "client": branding.client_name,
        "company": branding.company_name,
        "classification": branding.classification,
        "date": ctx.now.strftime("%d %B %Y"),
        "scan_date": ctx.data.observed_label,
        "document_id": branding.document_id,
        "version": branding.version,
    }
