from __future__ import annotations

from reports.base import RenderContext, Section
from reports.config import SectionConfig, flag, limit
from shared.definitions.reports import SectionGroup


class DnsRecordsConfig(SectionConfig):
    max_per_type: int = limit(15, title="Records per type", minimum=1, maximum=200)
    show_txt: bool = flag(True, title="Include TXT records")


class DnsRecordsSection(Section):
    name = "dns_records"
    title = "DNS records"
    description = "The zone as it answered at enrichment time."
    group = SectionGroup.INTELLIGENCE.value
    default_enabled = False
    config_model = DnsRecordsConfig

    def build(self, ctx: RenderContext, cfg: DnsRecordsConfig) -> dict | None:
        lookup = getattr(ctx.data.target, "dns_lookup", None)
        if lookup is None or not lookup.records:
            return None
        grouped: dict[str, list] = {}
        for record in lookup.records:
            kind = getattr(record.record_type, "value", str(record.record_type)).upper()
            if kind == "TXT" and not cfg.show_txt:
                continue
            grouped.setdefault(kind, []).append(record)
        if not grouped:
            return None
        return {
            "groups": [
                {"type": kind, "records": rows[: cfg.max_per_type], "total": len(rows)}
                for kind, rows in sorted(grouped.items())
            ],
            "queried_at": lookup.queried_at,
        }
