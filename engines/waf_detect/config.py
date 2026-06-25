from __future__ import annotations

from dataclasses import dataclass

from shared.services.scan_resolve import ResolvedScanConfig


@dataclass
class WafDetectConfig:
    enabled: bool

    @classmethod
    def from_resolved(cls, resolved: ResolvedScanConfig) -> WafDetectConfig:
        exp = resolved.phases.get("expansion", {}) or {}
        return cls(enabled=bool(exp.get("waf_detection", True)))
