from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig


class HostDiscoveryConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Find live hosts",
        description="Sweep a netblock for responsive hosts before port scanning.",
    )
