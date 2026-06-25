from __future__ import annotations

from dataclasses import dataclass

from shared.services.scan_resolve import ResolvedScanConfig


@dataclass
class ScreenshotConfig:
    enabled: bool
    threads: int
    timeout: int

    @classmethod
    def from_resolved(cls, resolved: ResolvedScanConfig) -> ScreenshotConfig:
        exp = resolved.phases.get("expansion", {}) or {}
        threads = resolved.resolved_threads or {}
        timeouts = resolved.resolved_timeouts or {}
        return cls(
            enabled=bool(exp.get("screenshot", True)),
            threads=int(
                threads.get("screenshot_threads")
                or exp.get("screenshot_threads")
                or 40
            ),
            timeout=int(
                timeouts.get("screenshot_timeout")
                or exp.get("screenshot_timeout")
                or 15
            ),
        )
