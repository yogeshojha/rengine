from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig, rate, threads, timeout


class OriginProbeConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Probe addresses directly",
        description="Request each address by IP and record what it serves without a hostname.",
    )
    threads: int = threads(30, title="Threads")
    timeout: int = timeout(10, title="Timeout (s)")
    rate: int = rate(150, tool="httpx", title="Requests/s")
    max_addresses: int = Field(
        default=2048,
        ge=1,
        le=65536,
        title="Address budget",
        description="Stop after this many addresses.",
    )
    max_ports_per_address: int = Field(
        default=6,
        ge=1,
        le=100,
        title="Ports per address",
        description="Cap the web ports requested on any one address.",
    )
