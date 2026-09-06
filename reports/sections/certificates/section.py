from __future__ import annotations

from reports.base import RenderContext, Section
from reports.config import SectionConfig, flag, limit
from shared.definitions.reports import SectionGroup
from shared.definitions.surface import SurfaceDimension


class CertificatesConfig(SectionConfig):
    expiring_days: int = limit(
        30, title="Treat as expiring within (days)", minimum=1, maximum=365
    )
    problems_only: bool = flag(True, title="Only certificates that need attention")
    max_rows: int = limit(50, title="Rows shown", minimum=5, maximum=1000)
    show_issuers: bool = flag(True, title="Show the issuer breakdown")


class CertificatesSection(Section):
    name = "certificates"
    title = "Certificates"
    description = (
        "Expired, expiring and self-signed certificates on assets that answered."
    )
    group = SectionGroup.SURFACE.value
    order = 50
    requires = frozenset({SurfaceDimension.WEB_ASSETS.value})
    config_model = CertificatesConfig

    def build(self, ctx: RenderContext, cfg: CertificatesConfig) -> dict | None:
        certificates = ctx.data.certificates
        if not certificates:
            return None
        expired = [c for c in certificates if c.expired]
        expiring = [
            c
            for c in certificates
            if not c.expired
            and c.days_left is not None
            and 0 <= c.days_left <= cfg.expiring_days
        ]
        self_signed = [c for c in certificates if c.self_signed]
        problems = sorted(
            {c.host: c for c in expired + expiring + self_signed}.values(),
            key=lambda c: c.days_left if c.days_left is not None else 9999,
        )
        rows = (
            problems
            if cfg.problems_only
            else sorted(
                certificates,
                key=lambda c: c.days_left if c.days_left is not None else 9999,
            )
        )
        if cfg.problems_only and not rows:
            return {
                "rows": [],
                "clean": True,
                "total": len(certificates),
                "expired": 0,
                "expiring": 0,
                "self_signed": 0,
                "issuers": [],
                "hidden": 0,
                "window": cfg.expiring_days,
            }
        issuers: dict[str, int] = {}
        for certificate in certificates:
            key = certificate.issuer or "Unknown"
            issuers[key] = issuers.get(key, 0) + 1
        return {
            "rows": rows[: cfg.max_rows],
            "clean": False,
            "total": len(certificates),
            "expired": len(expired),
            "expiring": len(expiring),
            "self_signed": len(self_signed),
            "hidden": max(0, len(rows) - cfg.max_rows),
            "window": cfg.expiring_days,
            "issuers": sorted(issuers.items(), key=lambda item: -item[1])[:8]
            if cfg.show_issuers
            else [],
        }
