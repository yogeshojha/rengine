from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig


class TargetEnrichmentConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Target enrichment",
        description="Resolve the target and attach DNS, WHOIS and BGP context.",
    )
