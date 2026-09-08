from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig, threads, timeout


class TargetEnrichmentConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Enabled",
        description="Resolve the target and attach DNS, WHOIS and BGP context.",
    )
    dns_threads: int = threads(30, title="DNS threads")
    dns_timeout: int = timeout(5, title="DNS timeout (s)")
