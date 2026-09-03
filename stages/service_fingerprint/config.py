from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig, threads, timeout


class ServiceFingerprintConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Fingerprint services",
        description="Identify the software behind every non-web port from its service banner.",
    )
    threads: int = threads(32, title="Concurrency")
    timeout: int = timeout(4, title="Timeout (s)")
    max_services: int = Field(
        default=2000,
        ge=1,
        le=50000,
        title="Service budget",
        description="Stop after this many ports in one scan.",
    )
    include_unknown: bool = Field(
        default=True,
        title="Include unrecognised ports",
        description="Also probe ports with no well-known service.",
    )
