from __future__ import annotations

from dataclasses import dataclass

from shared.services.scan_resolve import ResolvedScanConfig


@dataclass
class HttpProbeConfig:
    enabled: bool
    threads: int
    timeout: int
    follow_redirects: bool
    rate_limit: int | None

    @classmethod
    def from_resolved(cls, resolved: ResolvedScanConfig) -> HttpProbeConfig:
        exp = resolved.phases.get("expansion", {}) or {}
        rates = resolved.per_tool_rate_limits or {}
        timeouts = resolved.resolved_timeouts or {}
        follow = resolved.follow_redirects
        return cls(
            enabled=bool(exp.get("http_crawl", True)),
            threads=int(resolved.global_threads or 50),
            timeout=int(timeouts.get("http_timeout") or 10),
            follow_redirects=True if follow is None else bool(follow),
            rate_limit=rates.get("httpx") or resolved.global_rate_limit_ceiling,
        )
