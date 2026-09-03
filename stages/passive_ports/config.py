from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig


class PassivePortsConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Look up known exposure",
        description="Read ports already indexed for each address by internet-wide scanners.",
    )
    max_addresses: int = Field(
        default=1024,
        ge=1,
        le=65536,
        title="Address budget",
        description="Stop after this many address lookups.",
    )
