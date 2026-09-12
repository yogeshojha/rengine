from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig, rate, threads, timeout


class EndpointProbeConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Verify endpoints",
        description="Request the discovered URLs and record each status.",
    )
    threads: int = threads(40, title="Threads")
    timeout: int = timeout(10, title="Timeout (s)")
    rate: int = rate(150, tool="httpx", title="Requests/s")
    max_urls: int = Field(
        default=5000,
        ge=0,
        le=100000,
        title="URLs to verify",
        description="Endpoints requested. The rest stay unverified.",
    )
    skip_static: bool = Field(
        default=True,
        title="Skip images and media",
        description="Skip images, stylesheets, fonts and other static files.",
    )
    follow_redirects: bool = Field(
        default=False,
        title="Follow redirects",
        description="Follow 3xx redirects.",
    )
