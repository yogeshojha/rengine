from __future__ import annotations

from reports.base import RenderContext, Section
from reports.config import SectionConfig, choice, flag, paragraph
from shared.definitions.reports import SectionGroup, SectionRole
from shared.enums.scan import ACTIVITY_STATUS_LABELS
from shared.services.source_ip import addresses

_STANDARDS = {
    "": "None",
    "ptes": "Penetration Testing Execution Standard",
    "nist": "NIST SP 800-115",
    "osstmm": "OSSTMM 3",
    "owasp": "OWASP Web Security Testing Guide",
}


class MethodologyConfig(SectionConfig):
    show_stages: bool = flag(True, title="List stages")
    show_tools: bool = flag(True, title="List tools")
    show_timing: bool = flag(True, title="Show timing")
    show_scope: bool = flag(True, title="Show scope and exclusions")
    standard: str = choice("ptes", title="Reference standard", options=_STANDARDS)
    note: str = paragraph(
        "", title="Additional note", description="Markdown appended to this section."
    )


class MethodologySection(Section):
    name = "methodology"
    title = "Scope and methodology"
    description = "Scope, stages and tools."
    group = SectionGroup.APPENDIX.value
    order = 10
    role = SectionRole.FURNITURE.value
    config_model = MethodologyConfig

    def build(self, ctx: RenderContext, cfg: MethodologyConfig) -> dict:
        source = ctx.data
        scan = source.scan
        stages = []
        if cfg.show_stages:
            from stages.registry import stage_by_name  # noqa: PLC0415

            table = stage_by_name()
            for name, status in source.stage_results.items():
                spec = table[name]
                stages.append(
                    {
                        "title": spec.title,
                        "description": spec.description,
                        "result": ACTIVITY_STATUS_LABELS.get(status, status),
                    }
                )
        return {
            "scan": scan,
            "stages": stages,
            "tools": source.tools_used if cfg.show_tools else [],
            "excluded": source.excluded() if cfg.show_scope else {},
            "standard": _STANDARDS.get(cfg.standard, ""),
            "timing": cfg.show_timing,
            "note": cfg.note,
            "intensity": (scan.execution_config or {}).get("intensity")
            if scan
            else None,
            "context": scan.context_name if scan else None,
            "source_ips": addresses(scan.source_ip) if scan else [],
        }
