from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig


class ScreenshotConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Capture screenshots",
        description="Render live web assets to images.",
    )
    max_screenshots: int = Field(
        default=0,
        ge=0,
        le=100000,
        title="Screenshot budget",
        description="Most web assets to render, best first. 0 renders every one. Each render is a full headless browser, so a large estate takes a while.",
    )
