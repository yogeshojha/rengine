from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig, rate, threads, timeout


class HostDiscoveryConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Find live hosts",
        description="Sweep a netblock for responsive hosts before port scanning.",
    )
    rate: int = rate(150, tool="naabu", title="Packet rate (pps)")
    threads: int = threads(30, title="Concurrency")
    timeout: int = timeout(5, title="Timeout (s)")
