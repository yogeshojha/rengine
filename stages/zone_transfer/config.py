from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig


class ZoneTransferConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Report an open zone transfer",
        description="Record a finding when the zone handed over its contents during discovery.",
    )
