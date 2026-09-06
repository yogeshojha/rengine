from __future__ import annotations

from reports.base import RenderContext, Section
from reports.config import SectionConfig, choice, columns, flag, limit
from shared.definitions.reports import SectionGroup
from shared.definitions.surface import SurfaceDimension

_COLUMNS = {
    "status": "HTTP status",
    "title": "Page title",
    "ip": "Address",
    "tech": "Technology",
    "server": "Server",
    "cdn": "CDN or WAF",
    "asn": "Network",
    "tls": "Certificate expiry",
    "findings": "Findings",
}


class WebAssetsConfig(SectionConfig):
    only_live: bool = flag(
        True,
        title="Only hosts that answered",
        description="Hosts with no HTTP response are excluded.",
    )
    max_rows: int = limit(80, title="Rows shown", minimum=5, maximum=2000)
    fields: list[str] = columns(
        ["status", "title", "ip", "tech"], title="Columns", options=_COLUMNS
    )
    order: str = choice(
        "findings",
        title="Order",
        options={"findings": "Findings first", "status": "Status", "name": "Name"},
    )
    show_new: bool = flag(True, title="Mark hosts new since the previous run")


class WebAssetsSection(Section):
    name = "web_assets"
    title = "Web assets"
    description = "The hostname inventory, with the columns you choose."
    group = SectionGroup.SURFACE.value
    requires = frozenset({SurfaceDimension.WEB_ASSETS.value})
    config_model = WebAssetsConfig

    def build(self, ctx: RenderContext, cfg: WebAssetsConfig) -> dict | None:
        rows = ctx.data.live_hosts if cfg.only_live else ctx.data.host_rows
        if not rows:
            return None
        if cfg.order == "findings":
            rows = sorted(rows, key=lambda h: (-h.findings, h.name))
        elif cfg.order == "status":
            rows = sorted(rows, key=lambda h: (h.status or 999, h.name))
        else:
            rows = sorted(rows, key=lambda h: h.name)
        total = len(rows)
        return {
            "rows": rows[: cfg.max_rows],
            "total": total,
            "hidden": max(0, total - cfg.max_rows),
            "fields": [f for f in cfg.fields if f in _COLUMNS],
            "labels": _COLUMNS,
            "show_new": cfg.show_new,
            "only_live": cfg.only_live,
            "all_hosts": ctx.data.count_of(SurfaceDimension.WEB_ASSETS.value),
        }
