from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig, threads, timeout


class ReverseDnsConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Reverse DNS",
        description="Resolve PTR records for every discovered IP.",
    )
    dns_threads: int = threads(30, title="DNS threads")
    dns_timeout: int = timeout(5, title="DNS timeout (s)")
