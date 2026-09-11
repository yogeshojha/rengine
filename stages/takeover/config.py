from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig


class TakeoverConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Check for takeover",
        description="Report hostnames whose CNAME points at a provider but resolves nowhere.",
    )
