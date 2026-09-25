from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig


class NameOwnershipConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Check hostname ownership",
        description="Report hostnames that serve third-party content or resolve to a server with no site for them.",
    )
