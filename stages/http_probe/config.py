from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig, advanced


class HttpProbeConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Probe HTTP services",
        description="Fingerprint every host and port for live HTTP, technologies and titles.",
    )
    probe_all_ports: bool = advanced(
        False,
        title="Include non-web ports",
        description="Also probe ports classed as non-HTTP services.",
    )


FOLLOW_REDIRECTS = True
MAX_PORTS_PER_HOST = 25
