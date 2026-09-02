from __future__ import annotations

from typing import Literal

from pydantic import Field

from stages.config import StageConfig

_MAX_HOSTS = {"smart": 4096, "full": 65536}


class SeedResolutionConfig(StageConfig):
    asn_scan_mode: Literal["smart", "full"] = Field(
        default="smart",
        title="ASN / CIDR expansion",
        description="Smart samples large netblocks; full enumerates every host.",
    )
    cidr_skip_rfc1918: bool = Field(
        default=True,
        title="Skip private ranges",
        description="Drop RFC1918 addresses while expanding a netblock.",
    )

    @property
    def max_expansion_hosts(self) -> int:
        return _MAX_HOSTS[self.asn_scan_mode]
