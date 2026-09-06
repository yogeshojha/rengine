from __future__ import annotations

from sqlalchemy import select

from reports.base import RenderContext, Section
from reports.config import SectionConfig, limit
from shared.definitions.domains import PRIVATE_TLDS, registrable_domain
from shared.definitions.reports import SectionGroup
from shared.definitions.surface import SurfaceDimension
from shared.models.http_asset import HttpAsset

_VENDOR_HINTS = (
    "amazonaws",
    "cloudfront",
    "akamai",
    "azure",
    "googleusercontent",
    "fastly",
    "sni.cloudflare",
)


class ScopeRecommendationsConfig(SectionConfig):
    max_rows: int = limit(20, title="Suggestions shown", minimum=1, maximum=100)
    min_evidence: int = limit(
        1, title="Minimum certificates naming the domain", minimum=1, maximum=20
    )


class ScopeRecommendationsSection(Section):
    name = "scope_recommendations"
    title = "Domains worth adding to scope"
    description = "Other registrable domains named on certificates this estate serves."
    group = SectionGroup.INTELLIGENCE.value
    requires = frozenset({SurfaceDimension.WEB_ASSETS.value})
    default_enabled = False
    config_model = ScopeRecommendationsConfig

    def build(self, ctx: RenderContext, cfg: ScopeRecommendationsConfig) -> dict | None:
        scan_id = ctx.data.scan_for(SurfaceDimension.WEB_ASSETS.value)
        if scan_id is None:
            return None
        own = registrable_domain(ctx.data.subject) or ctx.data.subject
        rows = ctx.data.session.execute(
            select(HttpAsset.host, HttpAsset.tls_sans)
            .where(HttpAsset.scan_id == scan_id, HttpAsset.tls_sans.is_not(None))
            .limit(4000)
        ).all()

        found: dict[str, dict] = {}
        for host, sans in rows:
            for name in sans or []:
                cleaned = str(name).lstrip("*.").strip().lower()
                if not cleaned or "." not in cleaned:
                    continue
                apex = registrable_domain(cleaned)
                if not apex or apex == own:
                    continue
                if apex.rsplit(".", 1)[-1] in PRIVATE_TLDS:
                    continue
                if any(hint in apex for hint in _VENDOR_HINTS):
                    continue
                entry = found.setdefault(
                    apex, {"domain": apex, "names": set(), "seen_on": set()}
                )
                entry["names"].add(cleaned)
                entry["seen_on"].add(host)

        suggestions = [
            {
                "domain": entry["domain"],
                "names": sorted(entry["names"])[:4],
                "seen_on": sorted(entry["seen_on"])[:3],
                "count": len(entry["seen_on"]),
            }
            for entry in found.values()
            if len(entry["seen_on"]) >= cfg.min_evidence
        ]
        if not suggestions:
            return None
        suggestions.sort(key=lambda row: -row["count"])
        return {
            "rows": suggestions[: cfg.max_rows],
            "own": own,
            "total": len(suggestions),
        }
