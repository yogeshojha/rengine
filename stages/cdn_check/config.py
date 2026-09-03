from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig


class CdnCheckConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Attribute CDNs and cloud",
        description="Identify which addresses are fronted by a CDN, WAF or cloud provider.",
    )
