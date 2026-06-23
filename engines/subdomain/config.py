from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shared.services.scan_resolve import ResolvedScanConfig

_TOOL_TIMEOUTS = {"passive": 240, "normal": 360, "aggressive": 600}


@dataclass
class SubdomainConfig:
    enabled: bool
    passive: bool
    passive_tools: list[str]
    active: bool
    wordlist: str
    api_sources: dict[str, bool]
    tls_discovery: bool
    scraping: bool
    recursive: bool
    zone_transfer: bool
    intensity: str
    threads: int
    excluded_subdomains: list[str] = field(default_factory=list)
    included_subdomains: list[str] = field(default_factory=list)
    proxy_url: str | None = None
    tool_options: dict[str, str] = field(default_factory=dict)

    @property
    def tool_timeout(self) -> int:
        return _TOOL_TIMEOUTS.get(self.intensity, 360)

    @classmethod
    def from_resolved(cls, resolved: ResolvedScanConfig) -> SubdomainConfig:
        exp = resolved.phases.get("expansion", {}) or {}
        passive = bool(exp.get("subdomain_passive", False))
        active = bool(exp.get("subdomain_active", False))
        return cls(
            enabled=passive or active,
            passive=passive,
            passive_tools=list(exp.get("subdomain_passive_tools", []) or []),
            active=active,
            wordlist=exp.get("subdomain_wordlist", "") or "",
            api_sources={
                "securitytrails": bool(exp.get("subdomain_securitytrails", False)),
                "censys": bool(exp.get("subdomain_censys", False)),
                "virustotal": bool(exp.get("subdomain_virustotal", False)),
                "chaos": bool(exp.get("subdomain_chaos", False)),
                "binaryedge": bool(exp.get("subdomain_binaryedge", False)),
            },
            tls_discovery=bool(exp.get("subdomain_tls_discovery", False)),
            scraping=bool(exp.get("subdomain_scraping", False)),
            recursive=bool(exp.get("subdomain_recursive", False)),
            zone_transfer=bool(exp.get("dns_zone_transfer", False)),
            intensity=resolved.intensity or "normal",
            threads=int(resolved.resolved_threads.get("dns_threads", 30) or 30),
            excluded_subdomains=list(resolved.excluded_subdomains or []),
            included_subdomains=list(resolved.included_subdomains or []),
            proxy_url=resolved.proxy_url,
            tool_options=dict(resolved.tool_options or {}),
        )
