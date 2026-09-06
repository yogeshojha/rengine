from __future__ import annotations

from reports.base import RenderContext, Section
from reports.config import SectionConfig, choice, flag, paragraph
from shared.definitions.reports import SectionGroup

_STANDARDS = {
    "": "Do not cite a standard",
    "ptes": "Penetration Testing Execution Standard",
    "nist": "NIST SP 800-115",
    "osstmm": "OSSTMM 3",
    "owasp": "OWASP Web Security Testing Guide",
}


class MethodologyConfig(SectionConfig):
    show_stages: bool = flag(True, title="List what ran")
    show_tools: bool = flag(True, title="List the tools used")
    show_timing: bool = flag(True, title="Show when it ran and for how long")
    show_scope: bool = flag(True, title="Show scope and exclusions")
    standard: str = choice("ptes", title="Reference standard", options=_STANDARDS)
    note: str = paragraph(
        "", title="Additional note", description="Markdown appended to this section."
    )


class MethodologySection(Section):
    name = "methodology"
    title = "Scope and methodology"
    description = "What was in scope, what ran against it, and with which tools."
    group = SectionGroup.APPENDIX.value
    config_model = MethodologyConfig

    def build(self, ctx: RenderContext, cfg: MethodologyConfig) -> dict:
        source = ctx.data
        scan = source.scan
        stages = []
        if cfg.show_stages:
            try:
                from stages.registry import stages as specs  # noqa: PLC0415

                table = {spec.name: spec for spec in specs()}
            except ImportError:
                table = {}
            for name in source.planned_stages:
                spec = table.get(name)
                stages.append(
                    {
                        "name": name,
                        "title": spec.title if spec else name.replace("_", " ").title(),
                        "description": spec.description if spec else "",
                        "phase": spec.phase if spec else "",
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
        }
