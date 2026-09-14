from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig


class ReverseDnsConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Reverse DNS",
        description="Resolve PTR records for every discovered IP.",
    )
