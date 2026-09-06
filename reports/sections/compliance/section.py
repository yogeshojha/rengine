from __future__ import annotations

from reports.base import RenderContext, Section
from reports.config import SectionConfig, flag, multi
from shared.definitions.compliance import (
    DEFAULT_FRAMEWORKS,
    FRAMEWORK_BY_KEY,
    FRAMEWORK_KEYS,
)
from shared.definitions.reports import SectionGroup
from shared.definitions.surface import SurfaceDimension


class ComplianceConfig(SectionConfig):
    frameworks: list[str] = multi(
        list(DEFAULT_FRAMEWORKS),
        title="Frameworks",
        options={k: FRAMEWORK_BY_KEY[k].name for k in FRAMEWORK_KEYS},
    )
    show_empty: bool = flag(
        True,
        title="Show controls with no findings",
        description="An empty control is evidence too.",
    )
    show_scope_note: bool = flag(True, title="Show what the mapping does not cover")


class ComplianceSection(Section):
    name = "compliance"
    title = "Control mapping"
    description = "Findings mapped to control frameworks as audit evidence, not a compliance verdict."
    group = SectionGroup.FINDINGS.value
    requires = frozenset({SurfaceDimension.VULNERABILITIES.value})
    default_enabled = False
    config_model = ComplianceConfig

    def build(self, ctx: RenderContext, cfg: ComplianceConfig) -> dict | None:
        blocks = []
        for key in cfg.frameworks:
            spec = FRAMEWORK_BY_KEY.get(key)
            data = ctx.brief.compliance.get(key)
            if spec is None or data is None:
                continue
            counts = data["counts"]
            rows = [
                {
                    "id": control.id,
                    "title": control.title,
                    "note": control.note,
                    "count": counts.get(control.id, 0),
                    "evidence": control.id in data.get("evidence_only", []),
                }
                for control in spec.controls
                if cfg.show_empty
                or counts.get(control.id)
                or control.id in data.get("evidence_only", [])
            ]
            if not rows:
                continue
            blocks.append(
                {
                    "name": spec.name,
                    "version": spec.version,
                    "url": spec.url,
                    "scope_note": spec.scope_note if cfg.show_scope_note else "",
                    "rows": rows,
                    "total": sum(counts.values()),
                }
            )
        if not blocks:
            return None
        return {"blocks": blocks}
