"""Plug-and-play discovery: the classes a directory of modules or sub-packages declares."""

from __future__ import annotations

import importlib
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType

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
    """Concrete subclasses of `base` defined in `namespace`."""
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
    package: str, directory: Path, base: type[T]
) -> list[type[T]]:
    """Every `base` subclass declared by a module in `directory`."""
    found: list[type[T]] = []
    for module in sorted(directory.glob("*.py")):
        if module.stem.startswith("_") or module.stem in SKIP:
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
