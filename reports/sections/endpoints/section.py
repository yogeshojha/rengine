from __future__ import annotations

from reports.base import RenderContext, Section
from reports.config import SectionConfig, flag, limit
from shared.definitions.endpoints import (
    INTEREST_LABELS,
    STATIC_CLASSES,
    ParamInterest,
    PathInterest,
)
from shared.definitions.reports import SectionGroup
from shared.definitions.surface import SurfaceDimension

_NOTABLE = frozenset(
    {
        PathInterest.ADMIN.value,
        PathInterest.AUTH.value,
        PathInterest.API_DOC.value,
        PathInterest.DEBUG_ENDPOINT.value,
        PathInterest.INFRA.value,
        PathInterest.SECRETS.value,
        ParamInterest.UPLOAD.value,
    }
)


class EndpointsConfig(SectionConfig):
    notable_only: bool = flag(
        True,
        title="Only notable paths",
        description="Administrative, authentication, API and debug paths.",
    )
    hide_static: bool = flag(True, title="Hide static files")
    only_answering: bool = flag(True, title="Only paths that answered")
    max_rows: int = limit(60, title="Rows shown", minimum=5, maximum=2000)
    show_params: bool = flag(True, title="Show parameter names")


class EndpointsSection(Section):
    name = "endpoints"
    title = "Endpoints"
    description = "Administrative, authentication, API and debug paths."
    group = SectionGroup.SURFACE.value
    order = 30
    launch_fields = frozenset({"max_rows"})
    requires = frozenset({SurfaceDimension.ENDPOINTS.value})
    config_model = EndpointsConfig

    def build(self, ctx: RenderContext, cfg: EndpointsConfig) -> dict | None:
        rows = ctx.data.endpoint_rows
        if cfg.hide_static:
            rows = [e for e in rows if e.endpoint_class not in STATIC_CLASSES]
        if cfg.only_answering:
            rows = [e for e in rows if e.status]
        if cfg.notable_only:
            rows = [e for e in rows if _NOTABLE.intersection(e.interest or [])]
        if not rows:
            return None
        rows = sorted(rows, key=lambda e: (e.host, e.path))
        total = len(rows)
        return {
            "rows": [
                {
                    "endpoint": e,
                    "markers": [
                        INTEREST_LABELS.get(k, k) for k in (e.interest or [])[:2]
                    ],
                }
                for e in rows[: cfg.max_rows]
            ],
            "total": total,
            "hidden": max(0, total - cfg.max_rows),
            "show_params": cfg.show_params,
            "notable_only": cfg.notable_only,
            "all_endpoints": ctx.data.count_of(SurfaceDimension.ENDPOINTS.value),
        }
