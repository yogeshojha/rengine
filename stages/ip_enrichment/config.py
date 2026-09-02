from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig


class IpEnrichmentConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Enrich IPs",
        description="Attach ASN, prefix and WHOIS context to discovered IPs.",
    )
