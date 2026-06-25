from __future__ import annotations

from dataclasses import dataclass

from shared.services.scan_resolve import ResolvedScanConfig


@dataclass
class HostDiscoveryConfig:
    enabled: bool
    rate: int
    threads: int
    timeout: int

    @classmethod
    def from_resolved(cls, resolved: ResolvedScanConfig) -> HostDiscoveryConfig:
        exp = resolved.phases.get("expansion", {}) or {}
        rates = resolved.per_tool_rate_limits or {}
        return cls(
            enabled=bool(exp.get("port_scan_enabled", True)),
            rate=int(rates.get("naabu") or exp.get("port_scan_rate_limit") or 1000),
            threads=int(exp.get("port_scan_threads") or 30),
            timeout=int(exp.get("port_scan_timeout") or 5),
        )
