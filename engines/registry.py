"""Stages the orchestrator composes into the scan canvas (same level = parallel)."""

from __future__ import annotations

from dataclasses import dataclass

from engines.base import Engine
from engines.subdomain.engine import SubdomainEngine


@dataclass(frozen=True)
class StageSpec:
    name: str
    title: str
    level: int
    engine_cls: type[Engine]


STAGES: tuple[StageSpec, ...] = (
    StageSpec(
        name="subdomain_discovery",
        title="Subdomain Discovery",
        level=0,
        engine_cls=SubdomainEngine,
    ),
)

STAGE_BY_NAME: dict[str, StageSpec] = {s.name: s for s in STAGES}


def ordered_levels() -> list[list[StageSpec]]:
    """Stages grouped by level, levels ascending — the canvas execution order."""
    levels: dict[int, list[StageSpec]] = {}
    for spec in STAGES:
        levels.setdefault(spec.level, []).append(spec)
    return [levels[lvl] for lvl in sorted(levels)]
