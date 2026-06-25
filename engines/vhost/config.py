from __future__ import annotations

from dataclasses import dataclass

from shared.services.scan_resolve import ResolvedScanConfig

_DEFAULT_WORDLIST = "/app/tools/data/vhosts.txt"


@dataclass
class VhostConfig:
    enabled: bool
    wordlist: str
    threads: int
    rate: int

    @classmethod
    def from_resolved(cls, resolved: ResolvedScanConfig) -> VhostConfig:
        exp = resolved.phases.get("expansion", {}) or {}
        rates = resolved.per_tool_rate_limits or {}
        return cls(
            enabled=bool(exp.get("vhost_bruteforce", False)),
            wordlist=str(exp.get("vhost_wordlist") or _DEFAULT_WORDLIST),
            threads=int(resolved.global_threads or 40),
            rate=int(rates.get("ffuf") or 0),
        )
