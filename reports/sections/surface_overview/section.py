from __future__ import annotations

from reports.base import RenderContext, Section
from reports.config import SectionConfig, flag
from shared.definitions.reports import SectionGroup
from shared.definitions.surface import SURFACE_LABELS, SURFACE_NOUN, SURFACE_ORDER


class SurfaceOverviewConfig(SectionConfig):
    show_trend: bool = flag(
        True,
        title="Show trend",
        description="A sparkline over recent runs of this target.",
    )
    show_narrative: bool = flag(True, title="Show narrative")
    show_status: bool = flag(True, title="Show HTTP status split")


class SurfaceOverviewSection(Section):
    name = "surface_overview"
    title = "Attack surface"
    description = "Results in each dimension, and the dimensions not covered."
    group = SectionGroup.SUMMARY.value
    order = 40
    config_model = SurfaceOverviewConfig

    def build(self, ctx: RenderContext, cfg: SurfaceOverviewConfig) -> dict:
        rows = []
        for dimension in SURFACE_ORDER:
            entry = ctx.data.coverage[dimension]
            rows.append(
                {
                    "label": SURFACE_LABELS[dimension],
                    "noun": SURFACE_NOUN[dimension][1],
                    "covered": entry.covered,
                    "count": entry.count,
                    "previous": entry.previous,
                    "delta": entry.delta,
                    "observed": entry.observed_at,
                    "trend": ctx.data.trend(dimension)
                    if cfg.show_trend and entry.covered
                    else [],
                }
            )
        return {
            "rows": rows,
            "narrative": ctx.narrator.surface_narrative(ctx.brief)
            if cfg.show_narrative
            else "",
            "status": [f for f in ctx.data.status_classes if f.name != "none"]
            if cfg.show_status
            else [],
            "no_response": next(
                (f.count for f in ctx.data.status_classes if f.name == "none"), 0
            ),
            "hosting": ctx.brief.hosting,
        }
