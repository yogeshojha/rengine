from __future__ import annotations

from reports.base import RenderContext, Section
from reports.config import SectionConfig, flag, limit
from reports.sections import check_rows
from shared.definitions.hygiene import CHECKS, GROUP_LABELS
from shared.definitions.reports import SectionGroup
from shared.definitions.surface import SurfaceDimension


class WebHygieneConfig(SectionConfig):
    warnings_only: bool = flag(False, title="Only warning-level checks")
    show_hosts: bool = flag(True, title="List failing web assets")
    max_hosts: int = limit(40, title="Web assets listed", minimum=5, maximum=500)


class WebHygieneSection(Section):
    name = "web_hygiene"
    title = "Web hygiene"
    description = "Header checks on every web asset."
    group = SectionGroup.SURFACE.value
    order = 55
    requires = frozenset({SurfaceDimension.WEB_ASSETS.value})
    config_model = WebHygieneConfig

    def build(self, ctx: RenderContext, cfg: WebHygieneConfig) -> dict | None:
        hygiene = ctx.data.hygiene
        if hygiene is None or hygiene.evaluated == 0:
            return None
        rows = check_rows(
            CHECKS, GROUP_LABELS, hygiene.checks, warnings_only=cfg.warnings_only
        )
        hosts = hygiene.hosts[: cfg.max_hosts] if cfg.show_hosts else []
        return {
            "evaluated": hygiene.evaluated,
            "pending": hygiene.pending,
            "clean": hygiene.clean,
            "warning": hygiene.warning,
            "info": hygiene.info,
            "rows": rows,
            "hosts": hosts,
            "hidden": max(0, len(hygiene.hosts) - len(hosts)) if cfg.show_hosts else 0,
        }
