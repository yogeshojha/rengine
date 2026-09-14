from __future__ import annotations

from pydantic import Field

from shared.definitions.endpoints import DEFAULT_PROBE_CAP
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
        DEFAULT_PROBE_CAP,
        ge=0,
        le=100000,
        title="URLs to verify",
        description="Endpoints requested. The rest stay unverified.",
    )


FOLLOW_REDIRECTS = False
URL_DISCOVERY_STAGE = "url_discovery"
