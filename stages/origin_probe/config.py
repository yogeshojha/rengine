from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig, advanced


class OriginProbeConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Probe addresses directly",
        description="Request each address by IP and record what it serves without a hostname.",
    )
    max_addresses: int = advanced(
        2048,
        ge=1,
        le=65536,
        title="Address budget",
        description="Stop after this many addresses.",
    )


MAX_PORTS_PER_ADDRESS = 6
