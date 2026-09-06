from __future__ import annotations

from reports.base import RenderContext, Section
from reports.config import SectionConfig, flag, limit
from shared.definitions.reports import SectionGroup
from shared.definitions.surface import SurfaceDimension


class AppendixAssetsConfig(SectionConfig):
    include_hosts: bool = flag(True, title="Every hostname")
    include_addresses: bool = flag(True, title="Every address")
    include_services: bool = flag(False, title="Every service")
    include_findings: bool = flag(False, title="Every finding location")
    max_rows: int = limit(1500, title="Maximum rows per list", minimum=50, maximum=5000)


class AppendixAssetsSection(Section):
    name = "appendix_assets"
    title = "Asset inventory"
    description = "The full lists behind the figures."
    group = SectionGroup.APPENDIX.value
    order = 40
    launch_fields = frozenset({"max_rows"})
    default_enabled = False
    config_model = AppendixAssetsConfig

    def build(self, ctx: RenderContext, cfg: AppendixAssetsConfig) -> dict | None:
        blocks = []
        if cfg.include_hosts and ctx.data.host_rows:
            blocks.append(
                _block("Hostnames", [h.name for h in ctx.data.host_rows], cfg.max_rows)
            )
        if cfg.include_addresses and ctx.data.address_rows:
            blocks.append(
                _block("Addresses", [a.ip for a in ctx.data.address_rows], cfg.max_rows)
            )
        if cfg.include_services and ctx.data.service_rows:
            blocks.append(
                _block(
                    "Services",
                    [f"{s.ip}:{s.port}" for s in ctx.data.service_rows],
                    cfg.max_rows,
                )
            )
        if cfg.include_findings and ctx.data.findings:
            blocks.append(
                _block(
                    "Finding locations",
                    [f.matched_at for f in ctx.data.findings],
                    cfg.max_rows,
                )
            )
        if not blocks:
            return None
        return {"blocks": blocks}


def _block(label: str, values: list[str], limit_rows: int) -> dict:
    unique = sorted(dict.fromkeys(values))
    return {
        "label": label,
        "entries": unique[:limit_rows],
        "total": len(unique),
        "hidden": max(0, len(unique) - limit_rows),
        "dimension": SurfaceDimension.WEB_ASSETS.value,
    }
