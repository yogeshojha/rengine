from __future__ import annotations

from reports.base import RenderContext, Section
from reports.config import SectionConfig
from shared.definitions.reports import SectionGroup


class BgpConfig(SectionConfig):
    pass


class BgpSection(Section):
    name = "bgp"
    title = "Routing"
    description = "How the subject is announced on the global routing table."
    group = SectionGroup.INTELLIGENCE.value
    order = 30
    default_enabled = False
    config_model = BgpConfig

    def build(self, ctx: RenderContext, cfg: BgpConfig) -> dict | None:
        del cfg
        summary = getattr(ctx.data.target, "bgp_summary", None)
        if summary is None:
            return None
        facts = [
            ("Autonomous system", f"AS{summary.asn}" if summary.asn else ""),
            ("Holder", summary.holder or ""),
            ("Prefix", summary.prefix or ""),
            (
                "Prefixes announced",
                f"{summary.prefix_count:,}" if summary.prefix_count is not None else "",
            ),
            (
                "Peers",
                f"{summary.peer_count:,}" if summary.peer_count is not None else "",
            ),
            (
                "Announced",
                "Yes"
                if summary.announced
                else ("No" if summary.announced is not None else ""),
            ),
        ]
        rows = [(label, value) for label, value in facts if value]
        if not rows:
            return None
        return {"facts": rows, "queried_at": summary.queried_at}
