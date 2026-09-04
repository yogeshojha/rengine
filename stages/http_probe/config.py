from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig, rate, threads, timeout


class HttpProbeConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Probe HTTP services",
        description="Fingerprint every host and port for live HTTP, technologies and titles.",
    )
    threads: int = threads(30, title="Threads")
    timeout: int = timeout(10, title="Timeout (s)")
    rate: int = rate(150, tool="httpx", title="Requests/s")
    follow_redirects: bool = Field(
        default=True,
        title="Follow redirects",
        description="Follow 3xx to the final URL.",
    )
    probe_open_ports: bool = Field(
        default=True,
        title="Probe open ports",
        description="Probe the ports the port scan found, not only 80 and 443.",
    )
    probe_all_ports: bool = Field(
        default=False,
        title="Include non-web ports",
        description="Also probe ports whose service is known not to speak HTTP, such as SSH or MySQL.",
    )
    max_ports_per_host: int = Field(
        default=25,
        ge=1,
        le=1000,
        title="Ports per host",
        description="Cap the ports probed on any one host.",
    )
