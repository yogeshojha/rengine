from __future__ import annotations

from stages.config import StageConfig, threads, timeout


class TargetEnrichmentConfig(StageConfig):
    dns_threads: int = threads(30, title="DNS threads")
    dns_timeout: int = timeout(5, title="DNS timeout (s)")
