from __future__ import annotations

from dataclasses import dataclass

from shared.services.scan_resolve import ResolvedScanConfig

_SMART_MAX_HOSTS = 4096
_FULL_MAX_HOSTS = 65536


@dataclass
class DiscoveryStageConfig:
    asn_scan_mode: str
    cidr_skip_rfc1918: bool
    cidr_skip_cdn_ranges: bool
    ip_reverse_dns: bool
    dns_timeout: int
    dns_threads: int
    whois_timeout: int

    @property
    def max_expansion_hosts(self) -> int:
        return _FULL_MAX_HOSTS if self.asn_scan_mode == "full" else _SMART_MAX_HOSTS

    @classmethod
    def from_resolved(cls, resolved: ResolvedScanConfig) -> DiscoveryStageConfig:
        disc = resolved.phases.get("discovery", {}) or {}
        threads = resolved.resolved_threads or {}
        timeouts = resolved.resolved_timeouts or {}
        return cls(
            asn_scan_mode=str(disc.get("asn_scan_mode", "smart") or "smart"),
            cidr_skip_rfc1918=bool(disc.get("cidr_skip_rfc1918", True)),
            cidr_skip_cdn_ranges=bool(disc.get("cidr_skip_cdn_ranges", True)),
            ip_reverse_dns=bool(disc.get("ip_reverse_dns", True)),
            dns_timeout=int(
                timeouts.get("dns_timeout") or disc.get("dns_timeout") or 5
            ),
            dns_threads=int(
                threads.get("dns_threads") or disc.get("dns_threads") or 30
            ),
            whois_timeout=int(
                timeouts.get("whois_timeout") or disc.get("whois_timeout") or 10
            ),
        )
