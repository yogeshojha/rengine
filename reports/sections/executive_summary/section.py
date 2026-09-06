from __future__ import annotations

from reports.base import RenderContext, Section
from reports.config import SectionConfig, flag, paragraph
from shared.definitions.reports import SectionGroup
from shared.definitions.surface import SURFACE_LABELS, SURFACE_ORDER, SurfaceDimension
from shared.definitions.vulnerabilities import SEVERITY_LABELS, SEVERITY_ORDER, Severity


class ExecutiveSummaryConfig(SectionConfig):
    show_score: bool = flag(
        True,
        title="Show posture score",
        description="The dial and what deducted from it.",
    )
    show_kpis: bool = flag(True, title="Show surface figures")
    show_severity: bool = flag(True, title="Show severity distribution")
    show_deductions: bool = flag(True, title="Explain the score")
    preamble: str = paragraph(
        "", title="Opening note", description="Markdown printed before the narrative."
    )


class ExecutiveSummarySection(Section):
    name = "executive_summary"
    title = "Executive summary"
    description = "The narrative, the posture score and the figures behind both."
    group = SectionGroup.SUMMARY.value
    order = 10
    config_model = ExecutiveSummaryConfig

    def build(self, ctx: RenderContext, cfg: ExecutiveSummaryConfig) -> dict:
        brief = ctx.brief
        severity = [
            {
                "severity": key,
                "label": SEVERITY_LABELS[key],
                "count": brief.severity.get(key, 0),
            }
            for key in SEVERITY_ORDER
            if key != Severity.UNKNOWN.value
        ]
        assessed = any(
            c["covered"]
            for c in brief.coverage
            if c["dimension"] == SurfaceDimension.VULNERABILITIES.value
        )
        kpis = [
            {
                "dimension": key,
                "label": SURFACE_LABELS[key],
                "value": f"{ctx.data.coverage[key].count:,}"
                if ctx.data.coverage[key].covered
                else "Not scanned",
                "note": _note(ctx, key),
                "dash": not ctx.data.coverage[key].covered,
            }
            for key in SURFACE_ORDER
        ]
        return {
            "narrative": ctx.narrator.executive_summary(brief),
            "preamble": cfg.preamble,
            "posture": brief.posture if cfg.show_score else None,
            "score_arc": _arc(ctx, brief.posture.score),
            "deductions": brief.posture.deductions[:5] if cfg.show_deductions else [],
            "kpis": kpis if cfg.show_kpis else [],
            "severity": severity if cfg.show_severity and assessed else [],
            "assessed": assessed,
            "headline": brief.headline,
            "actionable": brief.actionable,
            "kev": brief.kev_count,
            "ai": ctx.narrator.ai_used and getattr(ctx.narrator, "used_model", False),
            "disclose": ctx.spec.narrative.disclose_ai,
        }


_GOOD, _FAIR = 80, 60


def _arc(ctx: RenderContext, score: int) -> str:
    if score >= _GOOD:
        return ctx.hue(1)
    if score >= _FAIR:
        return ctx.sev("medium")
    return ctx.sev("critical")


def _note(ctx: RenderContext, dimension: str) -> str:
    entry = ctx.data.coverage[dimension]
    if not entry.covered:
        return "no run produced this"
    if entry.previous is None:
        return ""
    delta = entry.count - entry.previous
    if delta > 0:
        return f"{delta:,} more than the previous run"
    if delta < 0:
        return f"{abs(delta):,} fewer than the previous run"
    return "unchanged"
