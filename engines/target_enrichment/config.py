from __future__ import annotations

from dataclasses import dataclass

from shared.services.scan_resolve import ResolvedScanConfig


@dataclass
class TargetEnrichmentConfig:
    dns_timeout: int
    dns_threads: int

    @classmethod
    def from_resolved(cls, resolved: ResolvedScanConfig) -> TargetEnrichmentConfig:
        disc = resolved.phases.get("discovery", {}) or {}
        threads = resolved.resolved_threads or {}
        timeouts = resolved.resolved_timeouts or {}
        return cls(
            dns_timeout=int(
                timeouts.get("dns_timeout") or disc.get("dns_timeout") or 5
            ),
            dns_threads=int(
                threads.get("dns_threads") or disc.get("dns_threads") or 30
            ),
        )
