"""Plug-and-play discovery: the classes a directory of modules or sub-packages declares."""

from __future__ import annotations

import importlib
from collections.abc import Collection, Iterable, Sequence
from dataclasses import fields
from functools import cache
from pathlib import Path
from types import ModuleType
from typing import Any, get_origin, get_type_hints

from pydantic import BaseModel

from shared.logging import get_logger

logger = get_logger(__name__)

SKIP = ("base",)


def _import(name: str) -> ModuleType | None:
    try:
        return importlib.import_module(name)
    except Exception as exc:
        logger.warning("plugin module skipped", module=name, error=str(exc))
        return None


def _declared[T](namespace: ModuleType, base: type[T]) -> list[type[T]]:
    """The subclasses this module declares itself, never the ones it imports."""
    out = []
    for obj in vars(namespace).values():
        if (
            isinstance(obj, type)
            and issubclass(obj, base)
            and obj is not base
            and obj.__module__ == namespace.__name__
            and not getattr(obj, "__abstractmethods__", None)
        ):
            out.append(obj)
    return out


def classes_in_modules[T](
    package: str, directory: Path, base: type[T], *, skip: Collection[str] = SKIP
) -> list[type[T]]:
    """Every `base` subclass declared by a module in `directory`."""
    found: list[type[T]] = []
    for module in sorted(directory.glob("*.py")):
        if module.stem.startswith("_") or module.stem in skip:
            continue
        namespace = _import(f"{package}.{module.stem}")
        if namespace is not None:
            found.extend(_declared(namespace, base))
    return found


def classes_in_packages[T](
    package: str,
    directory: Path,
    base: type[T],
    *,
    submodules: Sequence[str] = (),
) -> list[type[T]]:
    """Every `base` subclass declared by a sub-package of `directory`, or by `submodules` of one."""
    found: list[type[T]] = []
    for entry in sorted(directory.iterdir()):
        if not entry.is_dir() or entry.name.startswith(("_", ".")):
            continue
        for suffix in ("", *submodules):
            name = f"{package}.{entry.name}{'.' + suffix if suffix else ''}"
            namespace = _import_optional(name)
            if namespace is not None:
                found.extend(_declared(namespace, base))
    return found


def _import_optional(name: str) -> ModuleType | None:
    """A sub-package need not carry every module name a registry looks for."""
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as exc:
        if exc.name == name:
            return None
        logger.warning("plugin module skipped", module=name, error=str(exc))
        return None
    except Exception as exc:
        logger.warning("plugin module skipped", module=name, error=str(exc))
        return None


def by_name[T](
    classes: Iterable[type[T]], *, kind: str, error: type[Exception]
) -> dict[str, type[T]]:
    """Discovered classes keyed by their `name`.

    A class that sets no name, or two classes that claim the same one, is a
    registration error: a plugin is never dropped or shadowed in silence.
    """
    found: dict[str, type[T]] = {}
    for cls in classes:
        name = getattr(cls, "name", None)
        if not name:
            msg = f"{cls.__qualname__} must set a `name`."
            raise error(msg)
        existing = found.setdefault(name, cls)
        if existing is not cls:
            msg = (
                f"Duplicate {kind} name {name!r}: "
                f"{existing.__qualname__} and {cls.__qualname__}."
            )
            raise error(msg)
    return found


@cache
def _frozen_types(spec: type) -> dict[str, type | None]:
    """Per spec field, the immutable container a class attribute is copied into."""
    hints = get_type_hints(spec)
    out: dict[str, type | None] = {}
    for item in fields(spec):
        origin = get_origin(hints[item.name])
        out[item.name] = origin if origin in (frozenset, tuple) else None
    return out


def spec_of[S](spec: type[S], cls: type, **computed: Any) -> S:
    """A frozen spec of `cls`: every field not `computed` is its class attribute of that name."""
    values = dict(computed)
    for name, container in _frozen_types(spec).items():
        if name in values:
            continue
        value = getattr(cls, name)
        values[name] = container(value) if container is not None else value
    return spec(**values)


class ConfiguredSpec:
    """A registered plugin's settings: their defaults and their JSON schema."""

    config_model: type[BaseModel]

    @property
    def defaults(self) -> dict:
        return self.config_model().model_dump()

    @property
    def schema(self) -> dict:
        return self.config_model.model_json_schema()
