from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig, timeout


class SessionCheckConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Check the session before scanning",
        description="Ask the target once with the scan context's credentials and once without. Runs only when the context carries credentials.",
    )
    timeout: int = timeout(15, title="Timeout (s)")
