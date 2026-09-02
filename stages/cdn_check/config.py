from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig


class CdnCheckConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Detect CDNs",
        description="Flag hosts served from a CDN so port scans can skip them.",
    )
