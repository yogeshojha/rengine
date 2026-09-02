from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig, rate, threads, timeout


class PortScanConfig(StageConfig):
    enabled: bool = Field(
        default=True, title="Scan ports", description="Find open TCP ports on live hosts."
    )
    ports: str = Field(
        default="top-100",
        title="Ports",
        description="top-100, top-1000, full, or a list/range like 80,443,8000-8100.",
    )
    rate: int = rate(150, tool="naabu", title="Packet rate (pps)")
    threads: int = threads(30, title="Concurrency")
    timeout: int = timeout(5, title="Timeout (s)")
    exclude_cdn: bool = Field(
        default=True,
        title="Skip CDN hosts",
        description="Don't port scan hosts flagged as CDN-fronted.",
    )
