from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig, threads, timeout


class ScreenshotConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Capture screenshots",
        description="Render every live HTTP service to an image.",
    )
    threads: int = threads(40, title="Threads")
    timeout: int = timeout(10, title="Timeout (s)", description="Per-page render budget.")
