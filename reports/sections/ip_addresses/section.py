from __future__ import annotations

from reports.base import RenderContext, Section
from reports.config import SectionConfig, flag, limit
from shared.definitions.reports import SectionGroup
from shared.definitions.surface import SurfaceDimension


class IpAddressesConfig(SectionConfig):
    max_rows: int = limit(60, title="Rows shown", minimum=5, maximum=2000)
    show_ptr: bool = flag(False, title="Show reverse DNS")
    show_hosts: bool = flag(True, title="Show the hostnames on each address")
    only_open: bool = flag(False, title="Only addresses with an open port")


class IpAddressesSection(Section):
    name = "ip_addresses"
    title = "Addresses"
    description = "The address inventory with network, country and exposure."
    group = SectionGroup.SURFACE.value
    order = 40
    requires = frozenset({SurfaceDimension.IPS.value})
    config_model = IpAddressesConfig

    def build(self, ctx: RenderContext, cfg: IpAddressesConfig) -> dict | None:
        rows = ctx.data.address_rows
        if cfg.only_open:
            rows = [a for a in rows if a.open_ports]
        if not rows:
            return None
        rows = sorted(rows, key=lambda a: (-a.open_ports, a.ip))
        total = len(rows)
        return {
            "rows": rows[: cfg.max_rows],
            "total": total,
            "hidden": max(0, total - cfg.max_rows),
            "show_ptr": cfg.show_ptr,
            "show_hosts": cfg.show_hosts,
            "networks": len({a.asn for a in rows if a.asn}),
            "countries": len({a.country for a in rows if a.country}),
        }
