from __future__ import annotations

from dataclasses import dataclass

from shared.services.scan_resolve import ResolvedScanConfig


@dataclass
class CdnCheckConfig:
    enabled: bool

    @classmethod
    def from_resolved(cls, resolved: ResolvedScanConfig) -> CdnCheckConfig:
        exp = resolved.phases.get("expansion", {}) or {}
        return cls(enabled=bool(exp.get("cdn_detection", True)))
