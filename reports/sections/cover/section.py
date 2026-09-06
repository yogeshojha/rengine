from __future__ import annotations

from reports.base import RenderContext, Section
from reports.config import SectionConfig, choice, flag, text
from shared.definitions.reports import SectionGroup


class CoverConfig(SectionConfig):
    show_logo: bool = flag(
        True, title="Show logo", description="Print the uploaded logo on the cover."
    )
    show_meta: bool = flag(
        True,
        title="Show detail block",
        description="Client, author, date and document reference.",
    )
    show_classification: bool = flag(True, title="Show classification banner")
    show_grade: bool = flag(
        True,
        title="Show the posture grade",
        description="The letter grade and score on the cover, when vulnerabilities were assessed.",
    )
    kicker: str = text(
        "Attack surface report",
        title="Kicker",
        description="The small line above the title.",
    )
    date_style: str = choice(
        "long",
        title="Date format",
        options={
            "long": "12 September 2026",
            "short": "12 Sep 2026",
            "iso": "2026-09-12",
            "none": "No date",
        },
    )


def _grade(ctx: RenderContext) -> dict | None:
    assessed = any(
        c["covered"] for c in ctx.brief.coverage if c["dimension"] == "vulnerabilities"
    )
    if not assessed:
        return None
    posture = ctx.brief.posture
    return {"letter": posture.grade, "score": posture.score}


class CoverSection(Section):
    name = "cover"
    title = "Cover"
    description = "The title page. Layout and artwork come from the theme."
    group = SectionGroup.FRONT_MATTER.value
    in_toc = False
    config_model = CoverConfig

    def build(self, ctx: RenderContext, cfg: CoverConfig) -> dict:
        branding = ctx.branding
        fmt = {"long": "%d %B %Y", "short": "%d %b %Y", "iso": "%Y-%m-%d"}.get(
            cfg.date_style
        )
        meta: list[tuple[str, str]] = []
        if cfg.show_meta:
            pairs = (
                ("Prepared for", branding.prepared_for or branding.client_name),
                ("Prepared by", branding.prepared_by or branding.company_name),
                ("Assessed", ctx.data.observed_label),
                ("Report date", ctx.now.strftime(fmt) if fmt else ""),
                ("Reference", branding.document_id),
                ("Version", branding.version),
            )
            meta = [(label, value) for label, value in pairs if value]
        return {
            "bare": True,
            "kicker": cfg.kicker,
            "meta": meta,
            "logo": branding.company_logo if cfg.show_logo else "",
            "classification": branding.classification
            if cfg.show_classification
            else "",
            "art": ctx.theme.cover.art,
            "background": ctx.style.cover_image,
            "grade": _grade(ctx) if cfg.show_grade else None,
            "layout": ctx.theme.cover.layout,
            "accent_bar": ctx.theme.cover.accent_bar,
        }
