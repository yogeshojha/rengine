from __future__ import annotations

from dataclasses import dataclass

from shared.services.scan_resolve import ResolvedScanConfig

_SMART_MAX_HOSTS = 4096
_FULL_MAX_HOSTS = 65536


@dataclass
class SeedResolutionConfig:
    asn_scan_mode: str
    cidr_skip_rfc1918: bool

    @property
    def max_expansion_hosts(self) -> int:
        return _FULL_MAX_HOSTS if self.asn_scan_mode == "full" else _SMART_MAX_HOSTS

    @classmethod
    def from_resolved(cls, resolved: ResolvedScanConfig) -> SeedResolutionConfig:
        disc = resolved.phases.get("discovery", {}) or {}
        return cls(
            asn_scan_mode=str(disc.get("asn_scan_mode", "smart") or "smart"),
            cidr_skip_rfc1918=bool(disc.get("cidr_skip_rfc1918", True)),
        )
