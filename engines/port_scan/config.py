from __future__ import annotations

from dataclasses import dataclass

from shared.services.scan_resolve import ResolvedScanConfig


@dataclass
class PortScanConfig:
    enabled: bool
    ports: str
    rate: int
    threads: int
    timeout: int
    exclude_cdn: bool

    @classmethod
    def from_resolved(cls, resolved: ResolvedScanConfig) -> PortScanConfig:
        exp = resolved.phases.get("expansion", {}) or {}
        rates = resolved.per_tool_rate_limits or {}
        return cls(
            enabled=bool(exp.get("port_scan_enabled", True)),
            ports=str(exp.get("port_scan_ports") or "top-100"),
            rate=int(rates.get("naabu") or exp.get("port_scan_rate_limit") or 150),
            threads=int(exp.get("port_scan_threads") or 30),
            timeout=int(exp.get("port_scan_timeout") or 5),
            exclude_cdn=bool(exp.get("cdn_detection", True)),
        )
