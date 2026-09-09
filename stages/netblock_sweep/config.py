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
        description=(
            "How many of this scan's addresses must sit in a network "
            "before it is treated as the organisation's own."
        ),
    )
    max_asn_addresses: int = Field(
        default=65536,
        ge=256,
        le=1048576,
        title="Largest network an organisation may own",
        description=(
            "A network announcing more addresses than this is a transit or "
            "cloud provider rather than the target."
        ),
    )
    min_share: int = Field(
        default=10,
        ge=1,
        le=100,
        title="Share of the estate (%)",
        description=(
            "How much of the scan's addresses a network must hold. A small "
            "hosting or WAF provider carries a few; the organisation's own carries many."
        ),
    )
    max_sweep: int = Field(
        default=8192,
        ge=256,
        le=65536,
        title="Address budget",
        description=(
            "Most addresses to resolve. A larger range is swept up to this "
            "and the run is reported as partial."
        ),
    )
    dns_threads: int = threads(50, title="DNS threads")
    dns_timeout: int = timeout(5, title="DNS timeout (s)")
