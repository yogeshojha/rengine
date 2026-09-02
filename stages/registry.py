"""Stage registry — every Stage subclass under stages/ is discovered automatically."""

from __future__ import annotations

import contextlib
import importlib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import stages as stages_pkg
from shared.enums.scan import PHASE_ORDER
from stages.base import Stage
from stages.config import StageConfig


@dataclass(frozen=True)
class StageSpec:
    name: str
    title: str
    description: str
    phase: str
    level: int
    applies_to: frozenset[str]
    tools: tuple[str, ...]
    api_keys: tuple[str, ...]
    requires_api_keys: bool
    touches_target: bool
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
        for module in (f"stages.{package}", f"stages.{package}.stage", f"stages.{package}.engine"):
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


def _spec(stage_cls: type[Stage]) -> StageSpec:
    phase = stage_cls.phase
    if phase not in PHASE_ORDER:
        msg = f"{stage_cls.name}: unknown phase {phase!r}."
        raise StageRegistrationError(msg)
    return StageSpec(
        name=stage_cls.name,
        title=getattr(stage_cls, "title", None) or stage_cls.name.replace("_", " ").title(),
        description=stage_cls.description,
        phase=phase,
        level=stage_cls.level,
        applies_to=frozenset(stage_cls.applies_to),
        tools=tuple(stage_cls.tools),
        api_keys=tuple(stage_cls.api_keys),
        requires_api_keys=stage_cls.requires_api_keys,
        touches_target=stage_cls.touches_target,
        stage_cls=stage_cls,
        config_model=stage_cls.config_model,
    )


@lru_cache(maxsize=1)
def stages() -> tuple[StageSpec, ...]:
    specs = [_spec(cls) for cls in _stage_classes()]
    specs.sort(key=lambda s: (PHASE_ORDER.get(s.phase, 99), s.level, s.name))
    return tuple(specs)


def stage_by_name() -> dict[str, StageSpec]:
    return {spec.name: spec for spec in stages()}


def get_stage(name: str) -> StageSpec | None:
    return stage_by_name().get(name)


def ordered_levels() -> list[list[StageSpec]]:
    """Stages grouped by (phase, level), ascending — the canvas execution order."""
    groups: dict[tuple[int, int], list[StageSpec]] = {}
    for spec in stages():
        groups.setdefault((PHASE_ORDER.get(spec.phase, 99), spec.level), []).append(spec)
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
