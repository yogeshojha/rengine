from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig, rate, threads, timeout


class EndpointProbeConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Verify endpoints",
        description="Request the discovered URLs so every status is observed rather than inferred.",
    )
    threads: int = threads(40, title="Threads")
    timeout: int = timeout(10, title="Timeout (s)")
    rate: int = rate(150, tool="httpx", title="Requests/s")
    max_urls: int = Field(
        default=5000,
        ge=0,
        le=100000,
        title="URLs to verify",
        description="Cap the requests this stage sends. The endpoints it does not reach stay marked unverified.",
    )
    skip_static: bool = Field(
        default=True,
        title="Skip images and media",
        description="Do not spend the budget on content that carries no attack surface.",
    )
    follow_redirects: bool = Field(
        default=False,
        title="Follow redirects",
        description="Follow 3xx. Off by default so the recorded status is the endpoint's own.",
    )
