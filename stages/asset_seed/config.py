from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig


class AssetSeedConfig(StageConfig):
    enabled: bool = Field(
        default=False,
        title="Seed chosen assets",
        description="Start this run from assets picked in an earlier scan.",
    )
