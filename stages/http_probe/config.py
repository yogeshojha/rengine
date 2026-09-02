from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig, rate, threads, timeout


class HttpProbeConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Probe HTTP services",
        description="Fingerprint every host/port for live HTTP, tech and titles.",
    )
    threads: int = threads(30, title="Threads")
    timeout: int = timeout(10, title="Timeout (s)")
    rate: int = rate(150, tool="httpx", title="Requests/s")
    follow_redirects: bool = Field(
        default=True, title="Follow redirects", description="Follow 3xx to the final URL."
    )
