from __future__ import annotations

from typing import Literal

from pydantic import Field

from stages.config import StageConfig

_MAX_HOSTS = {"smart": 4096, "full": 65536}


class SeedResolutionConfig(StageConfig):
    asn_scan_mode: Literal["smart", "full"] = Field(
        default="smart",
        title="ASN / CIDR expansion",
        description="Smart samples large netblocks. Full enumerates every host.",
    )
    cidr_skip_rfc1918: bool = Field(
        default=True,
        title="Skip private ranges in ASN prefixes",
        description="Drop RFC1918 addresses while expanding the prefixes an ASN announces. A netblock target is always expanded in full.",
    )

    @property
    def max_expansion_hosts(self) -> int:
        return _MAX_HOSTS[self.asn_scan_mode]
