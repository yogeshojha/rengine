from __future__ import annotations

from reports.base import RenderContext, Section
from reports.config import SectionConfig, choice, flag, limit
from shared.definitions.reports import MAX_SCREENSHOTS, SectionGroup
from shared.definitions.surface import SurfaceDimension


class ScreenshotsConfig(SectionConfig):
    max_images: int = limit(
        12, title="Screenshots shown", minimum=1, maximum=MAX_SCREENSHOTS
    )
    columns: str = choice(
        "2", title="Per row", options={"1": "One", "2": "Two", "3": "Three"}
    )
    order: str = choice(
        "findings",
        title="Order",
        options={"findings": "Hosts with findings first", "name": "Name"},
    )
    show_title: bool = flag(True, title="Show the page title")


class ScreenshotsSection(Section):
    name = "screenshots"
    title = "Screenshots"
    description = "Screenshots of the assets. Images are embedded in the document."
    group = SectionGroup.SURFACE.value
    order = 70
    launch_fields = frozenset({"max_images"})
    requires = frozenset({SurfaceDimension.WEB_ASSETS.value})
    default_enabled = False
    config_model = ScreenshotsConfig

    def build(self, ctx: RenderContext, cfg: ScreenshotsConfig) -> dict | None:
        rows = [h for h in ctx.data.host_rows if h.screenshot]
        if not rows:
            return None
        rows = (
            sorted(rows, key=lambda h: (-h.findings, h.name))
            if cfg.order == "findings"
            else sorted(rows, key=lambda h: h.name)
        )
        return {
            "hosts": rows[: cfg.max_images],
            "columns": int(cfg.columns),
            "show_title": cfg.show_title,
            "total": len(rows),
        }
