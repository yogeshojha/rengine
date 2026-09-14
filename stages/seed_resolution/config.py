from __future__ import annotations

from typing import Literal

from pydantic import Field

from stages.config import StageConfig

_MAX_HOSTS = {"smart": 4096, "full": 65536}


class SeedResolutionConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Seed resolution",
        description="Expand an IP, netblock, ASN or URL seed into individual addresses.",
    )
    asn_scan_mode: Literal["smart", "full"] = Field(
        default="smart",
        title="ASN / CIDR expansion",
        description="Smart samples large netblocks. Full enumerates every host.",
    )

    @property
    def max_expansion_hosts(self) -> int:
        return _MAX_HOSTS[self.asn_scan_mode]
