from __future__ import annotations

from reports.base import RenderContext, Section
from reports.config import SectionConfig, flag, limit
from shared.definitions.reports import SectionGroup
from shared.definitions.surface import SURFACE_LABELS, SURFACE_NOUN


class ChangesConfig(SectionConfig):
    list_added: bool = flag(True, title="List what appeared")
    list_gone: bool = flag(True, title="List what went away")
    max_items: int = limit(
        20, title="Items listed per dimension", minimum=1, maximum=200
    )
    show_new_findings: bool = flag(
        True, title="Highlight findings this run reported first"
    )


class ChangesSection(Section):
    name = "changes"
    title = "Changes"
    description = "The difference against the previous run. Nothing is reported as new on a first run."
    group = SectionGroup.SUMMARY.value
    order = 50
    config_model = ChangesConfig

    def build(self, ctx: RenderContext, cfg: ChangesConfig) -> dict | None:
        if ctx.data.previous_scan is None:
            return {"first_run": True, "rows": [], "new_findings": []}
        rows = [
            {
                "label": SURFACE_LABELS[line.dimension],
                "noun": SURFACE_NOUN[line.dimension][1],
                "added": line.added,
                "gone": line.gone,
                "added_sample": line.added_sample[: cfg.max_items]
                if cfg.list_added
                else [],
                "gone_sample": line.gone_sample[: cfg.max_items]
                if cfg.list_gone
                else [],
            }
            for line in ctx.brief.changes
        ]
        new_findings = (
            [f for f in ctx.data.findings if f.is_new][:25]
            if cfg.show_new_findings
            else []
        )
        if not rows and not new_findings:
            return None
        return {
            "first_run": False,
            "rows": rows,
            "new_findings": new_findings,
            "previous": ctx.data.previous_scan,
        }
