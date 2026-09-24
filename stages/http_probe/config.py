from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig


class HttpProbeConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Probe HTTP services",
        description="Fingerprint every host and port for live HTTP, technologies and titles.",
    )


FOLLOW_REDIRECTS = True
MAX_PORTS_PER_HOST = 25
MENTION_ROUNDS = 2
MAX_MENTIONED = 5000
MENTION_RESOLVE_THREADS = 25
