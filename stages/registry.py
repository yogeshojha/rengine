"""Stage registry — every Stage subclass under stages/ is discovered automatically."""

from __future__ import annotations

import contextlib
import importlib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import stages as stages_pkg
from shared.enums.scan import PHASE_ORDER, AssetKind, StageGroup, StageRole
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
    launch_fields: tuple[str, ...]
    consumes: frozenset[str]
    produces: frozenset[str]
    group: str
    role: str
    stage_cls: type[Stage]
    config_model: type[StageConfig]

    @property
    def defaults(self) -> dict:
        return self.config_model().model_dump()

    @property
    def schema(self) -> dict:
        return self.config_model.model_json_schema()


class StageRegistrationError(RuntimeError):
    """An engine module declares an invalid or duplicate stage."""


_GROUPS = frozenset(g.value for g in StageGroup)
_ROLES = frozenset(r.value for r in StageRole)
_KINDS = frozenset(k.value for k in AssetKind)


def _stage_dirs() -> list[str]:
    # scanned by path, not pkgutil, so an engine needs no __init__.py
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
                    msg = f"Duplicate engine name {name!r}: {obj.__qualname__}."
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
        launch_fields=tuple(stage_cls.launch_fields),
        consumes=frozenset(stage_cls.consumes),
        produces=frozenset(stage_cls.produces),
        group=stage_cls.group,
        role=stage_cls.role,
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


def phases() -> list[tuple[str, list[StageSpec]]]:
    grouped: dict[str, list[StageSpec]] = {}
    for spec in stages():
        grouped.setdefault(spec.phase, []).append(spec)
    order = sorted(grouped, key=lambda p: PHASE_ORDER.get(p, 99))
    return [(phase, grouped[phase]) for phase in order]


def rate_tools() -> tuple[str, ...]:
    tools: list[str] = []
    for spec in stages():
        for tool in sorted(spec.config_model.rate_tools()):
            if tool not in tools:
                tools.append(tool)
    return tuple(tools)


__all__ = [
    "StageRegistrationError",
    "StageSpec",
    "get_stage",
    "ordered_levels",
    "phases",
    "rate_tools",
    "stage_by_name",
    "stages",
]
