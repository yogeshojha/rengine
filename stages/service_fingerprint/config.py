from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig, advanced


class ServiceFingerprintConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Fingerprint services",
        description="Identify the software behind every non-web port from its service banner.",
    )
    max_services: int = advanced(
        2000,
        ge=1,
        le=50000,
        title="Service budget",
        description="Stop after this many ports.",
    )
