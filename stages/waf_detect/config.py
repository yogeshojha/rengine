from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig


class WafDetectConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Detect WAFs",
        description="Fingerprint web application firewalls in front of live services.",
    )
