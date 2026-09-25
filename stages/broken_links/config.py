from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig


class BrokenLinksConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Check broken links",
        description="Report embedded scripts, frames and stylesheets loaded from a domain that no longer exists and can be registered.",
    )
