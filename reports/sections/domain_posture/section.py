from __future__ import annotations

from reports.base import RenderContext, Section
from reports.config import SectionConfig, flag, limit
from shared.definitions.domain_posture import CHECKS, GROUP_LABELS, SPF_ALL_LABELS
from shared.definitions.interest import TONE_WARNING
from shared.definitions.reports import SectionGroup
from shared.definitions.surface import SurfaceDimension


class DomainPostureConfig(SectionConfig):
    warnings_only: bool = flag(False, title="Only warning-level checks")
    show_zones: bool = flag(True, title="List zones")
    max_zones: int = limit(40, title="Zones listed", minimum=5, maximum=500)


class DomainPostureSection(Section):
    name = "domain_posture"
    title = "Domain posture"
    description = "SPF, DMARC, DKIM, MTA-STS, DNSSEC and CAA per zone."
    group = SectionGroup.SURFACE.value
    order = 56
    requires = frozenset({SurfaceDimension.WEB_ASSETS.value})
    config_model = DomainPostureConfig

    def build(self, ctx: RenderContext, cfg: DomainPostureConfig) -> dict | None:
        posture = ctx.data.domain_posture
        if posture is None or posture.evaluated == 0:
            return None
        counts = {c.key: c for c in posture.checks}
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
        zones = posture.zones[: cfg.max_zones] if cfg.show_zones else []
        return {
            "evaluated": posture.evaluated,
            "warning": posture.warning,
            "info": posture.info,
            "clean": posture.clean,
            "spoofable": posture.spoofable,
            "rows": rows,
            "zones": [
                {
                    "zone": z.zone,
                    "hosts": z.hosts,
                    "spf": SPF_ALL_LABELS.get(z.spf_all or "", "none"),
                    "dmarc": z.dmarc_policy or "none",
                    "dnssec": z.dnssec,
                    "checks": z.checks,
                }
                for z in zones
            ],
            "hidden": max(0, len(posture.zones) - len(zones)) if cfg.show_zones else 0,
        }
