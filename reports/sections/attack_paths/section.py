from __future__ import annotations

from reports.base import RenderContext, Section
from reports.config import SectionConfig, flag, limit
from shared.definitions.reports import SectionGroup


class AttackPathsConfig(SectionConfig):
    top: int = limit(6, title="Paths shown", minimum=1, maximum=20)
    show_assets: bool = flag(True, title="Show affected assets")
    show_evidence: bool = flag(True, title="Show evidence")


class AttackPathsSection(Section):
    name = "attack_paths"
    title = "Attack paths"
    description = "Conditions that combine into an attack route."
    group = SectionGroup.SUMMARY.value
    order = 30
    config_model = AttackPathsConfig

    def build(self, ctx: RenderContext, cfg: AttackPathsConfig) -> dict | None:
        paths = ctx.brief.paths[: cfg.top]
        if not paths:
            return None
        return {
            "paths": [
                {
                    "path": path,
                    "detail": ctx.narrator.attack_path(path),
                }
                for path in paths
            ],
            "show_assets": cfg.show_assets,
            "show_evidence": cfg.show_evidence,
        }
