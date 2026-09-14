"""Stage registry — every Stage subclass under stages/ is discovered automatically."""

from __future__ import annotations

import contextlib
import importlib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import stages as stages_pkg
from shared.definitions.intensity import PROFILES, RATE_TOOLS
from shared.enums.scan import PHASE_ORDER, AssetKind, Intensity, StageGroup, StageRole
from stages.base import Stage
from stages.config import StageConfig


@dataclass(frozen=True)
class StageSpec:
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

    @property
    def defaults(self) -> dict:
        return self.config_model().model_dump()

    @property
    def schema(self) -> dict:
        return self.config_model.model_json_schema()

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


def _stage_dirs() -> list[str]:
    names: set[str] = set()
    for root in stages_pkg.__path__:
        for entry in sorted(Path(root).iterdir()):
            if entry.is_dir() and not entry.name.startswith(("_", ".")):
                names.add(entry.name)
    return sorted(names)


def _stage_classes() -> list[type[Stage]]:
    found: dict[str, type[Stage]] = {}
    for package in _stage_dirs():
        namespaces = []
        for module in (
            f"stages.{package}",
            f"stages.{package}.stage",
            f"stages.{package}.engine",
        ):
            with contextlib.suppress(ModuleNotFoundError):
                namespaces.append(importlib.import_module(module))

        for namespace in namespaces:
            for obj in vars(namespace).values():
                if (
                    not isinstance(obj, type)
                    or not issubclass(obj, Stage)
                    or obj is Stage
                    or getattr(obj, "__abstractmethods__", None)
                ):
                    continue
                name = getattr(obj, "name", None)
                if not name:
                    msg = f"{obj.__qualname__} must set a `name`."
                    raise StageRegistrationError(msg)
                if found.setdefault(name, obj) is not obj:
                    msg = f"Duplicate stage name {name!r}: {obj.__qualname__}."
                    raise StageRegistrationError(msg)
    return list(found.values())


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
    return StageSpec(
        name=stage_cls.name,
        title=getattr(stage_cls, "title", None)
        or stage_cls.name.replace("_", " ").title(),
        description=stage_cls.description,
        phase=phase,
        level=level,
        depends_on=frozenset(stage_cls.depends_on),
        applies_to=frozenset(stage_cls.applies_to),
        tools=tuple(stage_cls.tools),
        api_keys=tuple(stage_cls.api_keys),
        requires_api_keys=stage_cls.requires_api_keys,
        touches_target=stage_cls.touches_target,
        passive_capable=stage_cls.passive_capable,
        deferrable=stage_cls.deferrable,
        launch_fields=tuple(stage_cls.launch_fields),
        catalog_hidden=stage_cls.catalog_hidden,
        always_on=stage_cls.always_on,
        consumes=frozenset(stage_cls.consumes),
        produces=frozenset(stage_cls.produces),
        group=stage_cls.group,
        role=stage_cls.role,
        transport_tool=stage_cls.transport_tool,
        rate_weight=stage_cls.rate_weight,
        thread_weight=stage_cls.thread_weight,
        transport_timeout=stage_cls.transport_timeout,
        stage_cls=stage_cls,
        config_model=stage_cls.config_model,
    )


def _levels(classes: list[type[Stage]]) -> dict[str, int]:
    """Longest-path depth per stage — the barrier a stage may not start before."""
    by_name = {cls.name: cls for cls in classes}
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
        for dep in by_name[name].depends_on:
            if dep not in by_name:
                msg = f"{name}: depends_on names unknown stage {dep!r}."
                raise StageRegistrationError(msg)
            value = max(value, _depth(dep) + 1)
        resolving.discard(name)
        depth[name] = value
        return value

    for name in by_name:
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
    """Stages nothing waits on, that touch the target and do not opt out."""
    awaited = {dep for spec in specs.values() for dep in spec.depends_on}
    wanted: set[str] = set()
    for spec in specs.values():
        for other in specs.values():
            if other.name != spec.name and (other.consumes & spec.produces):
                wanted.add(spec.name)
    return {
        name
        for name, spec in specs.items()
        if name not in awaited
        and name not in wanted
        and spec.touches_target
        and spec.deferrable
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
