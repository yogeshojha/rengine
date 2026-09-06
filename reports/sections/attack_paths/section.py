from __future__ import annotations

from reports.base import RenderContext, Section
from reports.config import SectionConfig, flag, limit
from shared.definitions.reports import SectionGroup


class AttackPathsConfig(SectionConfig):
    top: int = limit(6, title="Chains shown", minimum=1, maximum=20)
    show_assets: bool = flag(True, title="Name the affected assets")
    show_evidence: bool = flag(True, title="Show the observations behind each chain")


class AttackPathsSection(Section):
    name = "attack_paths"
    title = "Attack paths"
    description = "Conditions that chain into a route an attacker can take."
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
