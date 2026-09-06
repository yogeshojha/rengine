from __future__ import annotations

from reports.base import RenderContext, Section
from reports.config import SectionConfig, flag, limit, text
from shared.definitions.reports import SectionGroup
from shared.definitions.surface import SurfaceDimension


class RemediationPlanConfig(SectionConfig):
    top: int = limit(12, title="Actions listed", minimum=1, maximum=50)
    show_narrative: bool = flag(True, title="Show narrative")
    show_owner: bool = flag(
        True,
        title="Add an owner column",
        description="Printed blank for completion.",
    )
    show_due: bool = flag(True, title="Add a target date column")
    owner_label: str = text("Owner", title="Owner column heading")
    show_effort: bool = flag(True, title="Show the kind of change each action needs")


class RemediationPlanSection(Section):
    name = "remediation_plan"
    title = "Remediation plan"
    description = "Actions ordered by the risk they remove, with the reach of each."
    group = SectionGroup.FINDINGS.value
    order = 20
    launch_fields = frozenset({"top"})
    requires = frozenset({SurfaceDimension.VULNERABILITIES.value})
    config_model = RemediationPlanConfig

    def build(self, ctx: RenderContext, cfg: RemediationPlanConfig) -> dict | None:
        actions = ctx.brief.actions[: cfg.top]
        if not actions:
            return None
        return {
            "actions": actions,
            "narrative": ctx.narrator.remediation_plan(ctx.brief)
            if cfg.show_narrative
            else "",
            "total_clears": sum(a.clears for a in actions),
        }
