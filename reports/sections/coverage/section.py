from __future__ import annotations

from reports.base import RenderContext, Section
from reports.config import SectionConfig, flag
from shared.definitions.reports import SectionGroup
from shared.definitions.surface import SURFACE_LABELS, SURFACE_ORDER


class CoverageConfig(SectionConfig):
    show_scanner_runs: bool = flag(True, title="Show the scanner's own account")
    show_not_scanned: bool = flag(True, title="State what was not assessed")
    show_suppressed: bool = flag(True, title="Note suppressed findings")


class CoverageSection(Section):
    name = "coverage"
    title = "Coverage and limitations"
    description = "What ran, what did not, and what this report therefore cannot say."
    group = SectionGroup.APPENDIX.value
    config_model = CoverageConfig

    def build(self, ctx: RenderContext, cfg: CoverageConfig) -> dict:
        dimensions = [
            {
                "label": SURFACE_LABELS[dim],
                "covered": ctx.data.coverage[dim].covered,
                "count": ctx.data.coverage[dim].count,
            }
            for dim in SURFACE_ORDER
        ]
        rows = ctx.data.coverage_rows if cfg.show_scanner_runs else []
        caveats = [
            c
            for c in ctx.brief.caveats
            if cfg.show_not_scanned or c.kind != "not_scanned"
        ]
        if not cfg.show_suppressed:
            caveats = [c for c in caveats if c.kind != "suppressed"]
        return {"dimensions": dimensions, "runs": rows, "caveats": caveats}
