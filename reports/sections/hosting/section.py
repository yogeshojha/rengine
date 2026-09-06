from __future__ import annotations

from reports.base import RenderContext, Section
from reports.config import SectionConfig, flag, limit
from shared.definitions.reports import SectionGroup
from shared.definitions.surface import SurfaceDimension


class HostingConfig(SectionConfig):
    show_fronting: bool = flag(True, title="Show the CDN, cloud and origin split")
    show_networks: bool = flag(True, title="Show hosting networks")
    show_countries: bool = flag(True, title="Show where addresses resolve")
    show_tech: bool = flag(True, title="Show the technology stack")
    top: int = limit(10, title="Rows per list", minimum=3, maximum=30)


class HostingSection(Section):
    name = "hosting"
    title = "Hosting and infrastructure"
    description = (
        "The fronting, the networks carrying the surface and where it resolves."
    )
    group = SectionGroup.SURFACE.value
    order = 60
    requires = frozenset({SurfaceDimension.WEB_ASSETS.value})
    config_model = HostingConfig

    def build(self, ctx: RenderContext, cfg: HostingConfig) -> dict | None:
        hosting = ctx.brief.hosting
        if not hosting.get("hosts"):
            return None
        edge, cloud, direct = hosting["edge"], hosting["cloud"], hosting["direct"]
        return {
            "hosting": hosting,
            "fronting": [
                {"label": "CDN or WAF edge", "count": edge, "hue": 0},
                {"label": "Cloud provider", "count": cloud, "hue": 2},
                {"label": "Direct to origin", "count": direct, "hue": 1},
            ]
            if cfg.show_fronting and (edge or cloud or direct)
            else [],
            "networks": ctx.data.networks[: cfg.top] if cfg.show_networks else [],
            "countries": ctx.data.countries[: cfg.top] if cfg.show_countries else [],
            "tech": ctx.data.technologies[: cfg.top] if cfg.show_tech else [],
            "waf": hosting.get("waf", 0),
        }
