from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from shared.definitions.constants import DEFAULT_GLOBAL_THREADS
from shared.definitions.launch import (
    DEFAULT_LAUNCH_INTENSITY,
    MAX_LABEL_STAGES,
    QUICK_SCAN_LABEL,
)
from shared.services.scan_resolve import ResolvedScanConfig


@dataclass(frozen=True)
class AdHocEngine:
    """Engine-shaped defaults for a launch that names no saved engine."""

    name: str = QUICK_SCAN_LABEL
    intensity: str = DEFAULT_LAUNCH_INTENSITY
    global_threads: int = DEFAULT_GLOBAL_THREADS
    global_http_crawl: bool = True
    global_headers: tuple[str, ...] = ()
    stages: Mapping[str, dict] = field(default_factory=dict)
    tool_options: Mapping[str, str] = field(default_factory=dict)
    id: None = None


def plan_label(resolved: ResolvedScanConfig) -> str:
    """Name an ad hoc run after the capabilities it runs; support stages only count when nothing else does."""
    from shared.enums.scan import StageRole  # noqa: PLC0415
    from stages.registry import stages  # noqa: PLC0415

    running = [
        spec
        for spec in stages()
        if resolved.target_type in spec.applies_to
        and resolved.stage(spec.name).get("enabled")
    ]
    picked = [s for s in running if s.role == StageRole.CAPABILITY.value]
    titles = [spec.title for spec in (picked or running)]
    if not titles:
        return QUICK_SCAN_LABEL
    if len(titles) == 1:
        return titles[0]
    if len(titles) <= MAX_LABEL_STAGES:
        return f"{', '.join(titles[:-1])} and {titles[-1]}"
    return f"{QUICK_SCAN_LABEL} · {len(titles)} stages"
