from __future__ import annotations

from reports.base import RenderContext, Section
from reports.config import SectionConfig, flag, limit
from shared.definitions.endpoints import STATIC_CLASSES
from shared.definitions.reports import SectionGroup
from shared.definitions.surface import SurfaceDimension

_INTEREST = ("admin", "auth", "api_doc", "debug_endpoint", "infra", "upload", "secret")


class EndpointsConfig(SectionConfig):
    notable_only: bool = flag(
        True,
        title="Only notable paths",
        description="Administrative, authentication, API and debug paths rather than the whole crawl.",
    )
    hide_static: bool = flag(True, title="Hide static files")
    only_answering: bool = flag(True, title="Only paths that answered")
    max_rows: int = limit(60, title="Rows shown", minimum=5, maximum=2000)
    show_params: bool = flag(True, title="Show parameter names")


class EndpointsSection(Section):
    name = "endpoints"
    title = "Endpoints"
    description = (
        "The paths worth looking at, rather than every URL the crawl produced."
    )
    group = SectionGroup.SURFACE.value
    requires = frozenset({SurfaceDimension.ENDPOINTS.value})
    config_model = EndpointsConfig

    def build(self, ctx: RenderContext, cfg: EndpointsConfig) -> dict | None:
        rows = ctx.data.endpoint_rows
        if cfg.hide_static:
            rows = [e for e in rows if e.endpoint_class not in STATIC_CLASSES]
        if cfg.only_answering:
            rows = [e for e in rows if e.status]
        if cfg.notable_only:
            rows = [e for e in rows if set(e.interest or []) & set(_INTEREST)]
        if not rows:
            return None
        rows = sorted(rows, key=lambda e: (e.host, e.path))
        total = len(rows)
        return {
            "rows": rows[: cfg.max_rows],
            "total": total,
            "hidden": max(0, total - cfg.max_rows),
            "show_params": cfg.show_params,
            "notable_only": cfg.notable_only,
            "all_endpoints": ctx.data.count_of(SurfaceDimension.ENDPOINTS.value),
        }
