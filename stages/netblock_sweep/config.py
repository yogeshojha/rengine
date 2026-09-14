from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig, advanced


class NetblockSweepConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Netblock sweep",
        description="Resolve reverse DNS across the network ranges the organisation announces.",
    )
    max_sweep: int = advanced(
        8192,
        ge=256,
        le=65536,
        title="Address budget",
        description="Addresses resolved at most. A larger range is reported as partial.",
    )


MIN_ADDRESSES = 2
MIN_SHARE = 10
MAX_ASN_ADDRESSES = 65536
