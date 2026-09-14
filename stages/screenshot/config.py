from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig


class ScreenshotConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Capture screenshots",
        description="Render every live HTTP service to an image.",
    )
