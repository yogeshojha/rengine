from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig, threads, timeout


class NetblockSweepConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Netblock sweep",
        description="Resolve reverse DNS across the network ranges the organisation announces.",
    )
    min_addresses: int = Field(
        default=2,
        ge=1,
        le=100,
        title="Addresses before a network counts",
        description="Minimum number of the scan's addresses a network must hold to count as owned.",
    )
    max_asn_addresses: int = Field(
        default=65536,
        ge=256,
        le=1048576,
        title="Largest network an organisation may own",
        description="Networks announcing more addresses than this are excluded.",
    )
    min_share: int = Field(
        default=10,
        ge=1,
        le=100,
        title="Share of the estate (%)",
        description="Minimum share of the scan's addresses a network must hold.",
    )
    max_sweep: int = Field(
        default=8192,
        ge=256,
        le=65536,
        title="Address budget",
        description="Addresses resolved at most. A larger range is reported as partial.",
    )
    dns_threads: int = threads(50, title="DNS threads")
    dns_timeout: int = timeout(5, title="DNS timeout (s)")
