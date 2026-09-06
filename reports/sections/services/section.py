from __future__ import annotations

from reports.base import RenderContext, Section
from reports.config import SectionConfig, flag, limit
from shared.definitions.ports import SERVICE_CLASS_LABELS
from shared.definitions.reports import SectionGroup
from shared.definitions.surface import SurfaceDimension


class ServicesConfig(SectionConfig):
    max_rows: int = limit(60, title="Rows shown", minimum=5, maximum=2000)
    sensitive_first: bool = flag(True, title="List sensitive services first")
    hide_web: bool = flag(
        False,
        title="Hide services that answer HTTP",
        description="Web services already appear under web assets.",
    )
    show_composition: bool = flag(True, title="Show the class composition")
    show_banner: bool = flag(True, title="Show the software banner")
    show_coverage: bool = flag(
        True, title="Show what the port scan was allowed to touch"
    )


class ServicesSection(Section):
    name = "services"
    title = "Network services"
    description = "What is listening, on which address, and which of it is web."
    group = SectionGroup.SURFACE.value
    order = 20
    launch_fields = frozenset({"max_rows"})
    requires = frozenset({SurfaceDimension.SERVICES.value})
    config_model = ServicesConfig

    def build(self, ctx: RenderContext, cfg: ServicesConfig) -> dict | None:
        rows = ctx.data.service_rows
        if cfg.hide_web:
            rows = [s for s in rows if not s.is_http]
        if not rows:
            return None
        if cfg.sensitive_first:
            rows = sorted(rows, key=lambda s: (not s.sensitive, s.ip, s.port))
        total = len(rows)
        policies: dict[str, int] = {}
        for address in ctx.data.address_rows:
            if address.scan_policy:
                policies[address.scan_policy] = policies.get(address.scan_policy, 0) + 1
        return {
            "rows": rows[: cfg.max_rows],
            "total": total,
            "hidden": max(0, total - cfg.max_rows),
            "classes": [
                {
                    "name": f.name,
                    "label": SERVICE_CLASS_LABELS.get(f.name, f.name.title()),
                    "count": f.count,
                }
                for f in ctx.data.service_classes
            ]
            if cfg.show_composition
            else [],
            "sensitive": len(ctx.data.sensitive_services),
            "web": sum(1 for s in ctx.data.service_rows if s.is_http),
            "addresses": len({s.ip for s in ctx.data.service_rows}),
            "show_banner": cfg.show_banner,
            "policies": policies if cfg.show_coverage else {},
        }
