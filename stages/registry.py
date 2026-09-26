"""Stage registry — every Stage subclass under stages/ is discovered automatically."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import stages as stages_pkg
from shared.definitions.intensity import PROFILES, RATE_TOOLS
from shared.enums.scan import PHASE_ORDER, AssetKind, Intensity, StageGroup, StageRole
from shared.plugins import ConfiguredSpec, by_name, classes_in_packages, spec_of
from stages.base import Stage
from stages.config import StageConfig


@dataclass(frozen=True)
class StageSpec(ConfiguredSpec):
    """A registered stage: its class attributes, frozen, plus its dependency level.

    Every field but `level` and `stage_cls` is read off the stage class under
    the same name by `spec_of`, so a new `Stage` ClassVar needs only a field here.
    """

    name: str
    title: str
    description: str
    phase: str
    level: int
    depends_on: frozenset[str]
    applies_to: frozenset[str]
    tools: tuple[str, ...]
    api_keys: tuple[str, ...]
    requires_api_keys: bool
    touches_target: bool
    passive_capable: bool
    deferrable: bool
    launch_fields: tuple[str, ...]
    catalog_hidden: bool
    always_on: bool
    consumes: frozenset[str]
    produces: frozenset[str]
    group: str
    role: str
    transport_tool: str | None
    rate_weight: float
    thread_weight: float
    transport_timeout: int | None
    stage_cls: type[Stage]
    config_model: type[StageConfig]

    def transport(self, intensity: str, **scaling):
        """The stage's transport under this intensity, or None when it runs no tool."""
        if self.transport_tool is None:
            return None
        return self.stage_cls.default_transport(intensity, **scaling)


class StageRegistrationError(RuntimeError):
    """A stage module declares an invalid or duplicate stage."""


_GROUPS = frozenset(g.value for g in StageGroup)
_ROLES = frozenset(r.value for r in StageRole)
_KINDS = frozenset(k.value for k in AssetKind)


def _stage_classes() -> list[type[Stage]]:
    found = (
        obj
        for root in stages_pkg.__path__
        for obj in classes_in_packages(
            "stages", Path(root), Stage, submodules=("stage", "engine")
        )
    )
    return list(by_name(found, kind="stage", error=StageRegistrationError).values())


def _spec(stage_cls: type[Stage], level: int) -> StageSpec:
    phase = stage_cls.phase
    if phase not in PHASE_ORDER:
        msg = f"{stage_cls.name}: unknown phase {phase!r}."
        raise StageRegistrationError(msg)
    if stage_cls.group not in _GROUPS:
        msg = f"{stage_cls.name}: group must be one of {sorted(_GROUPS)}."
        raise StageRegistrationError(msg)
    if stage_cls.role not in _ROLES:
        msg = f"{stage_cls.name}: role must be one of {sorted(_ROLES)}."
        raise StageRegistrationError(msg)
    unknown = (set(stage_cls.consumes) | set(stage_cls.produces)) - _KINDS
    if unknown:
        msg = f"{stage_cls.name}: unknown asset kind {sorted(unknown)[0]!r}."
        raise StageRegistrationError(msg)
    tool = stage_cls.transport_tool
    if tool is not None and tool not in PROFILES[Intensity.NORMAL.value]:
        msg = f"{stage_cls.name}: no transport profile for {tool!r}."
        raise StageRegistrationError(msg)
    return spec_of(
        StageSpec,
        stage_cls,
        title=getattr(stage_cls, "title", None)
        or stage_cls.name.replace("_", " ").title(),
        level=level,
        stage_cls=stage_cls,
    )


def _levels(classes: list[type[Stage]]) -> dict[str, int]:
    """Longest-path depth per stage — the barrier a stage may not start before."""
    classes_by_name = {cls.name: cls for cls in classes}
    depth: dict[str, int] = {}
    resolving: set[str] = set()

    def _depth(name: str) -> int:
        if name in depth:
            return depth[name]
        if name in resolving:
            msg = f"Stage dependency cycle through {name!r}."
            raise StageRegistrationError(msg)
        resolving.add(name)
        value = 0
        for dep in classes_by_name[name].depends_on:
            if dep not in classes_by_name:
                msg = f"{name}: depends_on names unknown stage {dep!r}."
                raise StageRegistrationError(msg)
            value = max(value, _depth(dep) + 1)
        resolving.discard(name)
        depth[name] = value
        return value

    for name in classes_by_name:
        _depth(name)
    return depth


@lru_cache(maxsize=1)
def stages() -> tuple[StageSpec, ...]:
    classes = _stage_classes()
    depth = _levels(classes)
    specs = [_spec(cls, depth[cls.name]) for cls in classes]
    specs.sort(key=lambda s: (PHASE_ORDER.get(s.phase, 99), s.level, s.name))
    return tuple(specs)


def stage_by_name() -> dict[str, StageSpec]:
    return {spec.name: spec for spec in stages()}


def get_stage(name: str) -> StageSpec | None:
    return stage_by_name().get(name)


def ordered_levels() -> list[list[StageSpec]]:
    """Stages grouped by dependency depth, ascending — the canvas execution order."""
    groups: dict[int, list[StageSpec]] = {}
    for spec in stages():
        groups.setdefault(spec.level, []).append(spec)
    return [groups[key] for key in sorted(groups)]


def _deferrable(specs: dict[str, StageSpec]) -> set[str]:
    """Leaves that do not opt out: one that sends traffic, or a passive one past the last awaited level."""
    awaited = {dep for spec in specs.values() for dep in spec.depends_on}
    wanted: set[str] = set()
    for spec in specs.values():
        for other in specs.values():
            if other.name != spec.name and (other.consumes & spec.produces):
                wanted.add(spec.name)
    latest = max(
        (spec.level for name, spec in specs.items() if name in awaited | wanted),
        default=-1,
    )
    return {
        name
        for name, spec in specs.items()
        if name not in awaited
        and name not in wanted
        and spec.deferrable
        and (spec.touches_target or spec.level > latest)
    }


def execution_plan(
    start_level: int = 0, done: frozenset[str] | None = None
) -> list[tuple[str, ...]]:
    """The scan's steps."""
    done = done or frozenset()
    specs = {spec.name: spec for spec in stages()}
    deferred = _deferrable(specs)

    steps: list[tuple[str, ...]] = []
    tail: list[str] = []
    placed: dict[str, int] = {}
    for level in ordered_levels()[start_level:]:
        names = sorted(spec.name for spec in level if spec.name not in done)
        tail.extend(name for name in names if name in deferred)
        gating = tuple(name for name in names if name not in deferred)
        if gating:
            steps.append(gating)
            placed.update(dict.fromkeys(gating, len(steps) - 1))
    last = len(steps) - 1
    for name in tail:
        after = max(
            (placed[d] for d in specs[name].depends_on if d in placed), default=-1
        )
        index = max(last, after + 1)
        while index >= len(steps):
            steps.append(())
        steps[index] = tuple(sorted({*steps[index], name}))
        placed[name] = index
    return steps


def resume_level(done: frozenset[str]) -> int:
    """The first level still holding a stage that has not finished."""
    levels = ordered_levels()
    for index, level in enumerate(levels):
        if not all(spec.name in done for spec in level):
            return index
    return len(levels)


def resume_point(activities) -> tuple[int, set[str], int]:
    """The level a resumed canvas starts at, the stages it skips, and how many it will run."""
    from shared.services.orchestrator import stages_done  # noqa: PLC0415

    done = stages_done(activities)
    level = resume_level(frozenset(done))
    left = sum(len(step) for step in execution_plan(level, frozenset(done)))
    return level, done, left


def phases() -> list[tuple[str, list[StageSpec]]]:
    grouped: dict[str, list[StageSpec]] = {}
    for spec in stages():
        grouped.setdefault(spec.phase, []).append(spec)
    order = sorted(grouped, key=lambda p: PHASE_ORDER.get(p, 99))
    return [(phase, grouped[phase]) for phase in order]


def rate_tools() -> tuple[str, ...]:
    used = {spec.transport_tool for spec in stages()}
    return tuple(tool for tool in RATE_TOOLS if tool in used)


__all__ = [
    "StageRegistrationError",
    "StageSpec",
    "execution_plan",
    "get_stage",
    "ordered_levels",
    "phases",
    "rate_tools",
    "stage_by_name",
    "stages",
]
