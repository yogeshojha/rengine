from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig


class NameOwnershipConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Check name ownership",
        description="Report owned names answered by another organisation's server.",
    )
