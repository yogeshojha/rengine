from __future__ import annotations

from reports.base import RenderContext, Section
from reports.config import SectionConfig, flag, limit
from shared.definitions.hygiene import CHECKS, GROUP_LABELS
from shared.definitions.interest import TONE_WARNING
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
        counts = {c.key: c for c in hygiene.checks}
        rows = []
        for spec in CHECKS:
            count = counts.get(spec.key)
            if count is None or count.applicable == 0:
                continue
            if cfg.warnings_only and spec.tone != TONE_WARNING:
                continue
            rows.append(
                {
                    "label": spec.label,
                    "help": spec.help,
                    "group": GROUP_LABELS[spec.group],
                    "tone": spec.tone,
                    "failing": count.failing,
                    "applicable": count.applicable,
                    "share": round(count.failing / count.applicable * 100)
                    if count.applicable
                    else 0,
                }
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
