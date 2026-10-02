from __future__ import annotations

from pydantic import Field

from shared.definitions.intensity import Transport
from stages.config import StageConfig, advanced


class EndpointProbeConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Verify endpoints",
        description="Request the discovered URLs and record each status.",
    )
    skip_static: bool = advanced(
        True,
        title="Skip images and media",
        description="Skip images, stylesheets, fonts and other static files.",
    )
    max_urls: int = advanced(
        0,
        ge=0,
        le=100000,
        title="URLs to verify",
        description="Most endpoints to request, best first. 0 fits the list to 30 minutes at the scan's rate.",
    )


FOLLOW_REDIRECTS = False
URL_DISCOVERY_STAGE = "url_discovery"
# the automatic budget's window
PROBE_SECONDS = 1800


def probe_budget(transport: Transport) -> int:
    """Endpoints the probe requests in PROBE_SECONDS, one request a second per thread at most."""
    per_second = min(transport.rate or transport.threads, transport.threads)
    return max(1, per_second) * PROBE_SECONDS
