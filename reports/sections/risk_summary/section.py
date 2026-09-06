from __future__ import annotations

from reports.base import RenderContext, Section
from reports.config import SectionConfig, flag, limit
from shared.definitions.reports import SectionGroup
from shared.definitions.surface import SurfaceDimension
from shared.definitions.vulnerabilities import SEVERITY_LABELS, SEVERITY_ORDER


class RiskSummaryConfig(SectionConfig):
    top: int = limit(10, title="Ranked risks shown", minimum=3, maximum=40)
    show_donut: bool = flag(True, title="Show severity ring")
    show_concentration: bool = flag(True, title="Show where risk concentrates")
    show_narrative: bool = flag(True, title="Show narrative")
    show_signals: bool = flag(
        True,
        title="Show ranking signals",
        description="Why a finding outranks another of the same severity.",
    )


class RiskSummarySection(Section):
    name = "risk_summary"
    title = "Risk summary"
    description = "Severity distribution, the ranked weaknesses and where they cluster."
    group = SectionGroup.SUMMARY.value
    requires = frozenset({SurfaceDimension.VULNERABILITIES.value})
    config_model = RiskSummaryConfig

    def build(self, ctx: RenderContext, cfg: RiskSummaryConfig) -> dict | None:
        brief = ctx.brief
        if not brief.severity and not brief.risks:
            return None
        severity = [
            {
                "severity": key,
                "label": SEVERITY_LABELS[key],
                "count": brief.severity.get(key, 0),
            }
            for key in SEVERITY_ORDER
            if brief.severity.get(key)
        ]
        return {
            "severity": severity,
            "show_donut": cfg.show_donut,
            "risks": brief.risks[: cfg.top],
            "show_signals": cfg.show_signals,
            "concentration": brief.concentration[:8] if cfg.show_concentration else [],
            "narrative": ctx.narrator.risk_narrative(brief)
            if cfg.show_narrative
            else "",
            "actionable": brief.actionable,
            "total": sum(brief.severity.values()),
            "kev": brief.kev_count,
        }
