"""Providers are discovered from disk. Adding one is a directory, never a registry edit."""

from __future__ import annotations

import contextlib
import importlib
from functools import lru_cache
from pathlib import Path

from interest.base import InterestProvider

PROVIDER_DIR = Path(__file__).resolve().parent / "providers"


class ProviderRegistrationError(RuntimeError):
    """A provider module is invalid or duplicated."""


def _package_names() -> list[str]:
    if not PROVIDER_DIR.is_dir():
        return []
    return sorted(
        entry.name
        for entry in PROVIDER_DIR.iterdir()
        if entry.is_dir() and not entry.name.startswith(("_", "."))
    )


def _classes() -> list[type[InterestProvider]]:
    found: dict[str, type[InterestProvider]] = {}
    for package in _package_names():
        namespaces = []
        for module in (
            f"interest.providers.{package}.provider",
            f"interest.providers.{package}",
        ):
            with contextlib.suppress(ModuleNotFoundError):
                namespaces.append(importlib.import_module(module))
        for namespace in namespaces:
            for obj in vars(namespace).values():
                if (
                    not isinstance(obj, type)
                    or not issubclass(obj, InterestProvider)
                    or obj is InterestProvider
                    or not obj.name
                ):
                    continue
                existing = found.get(obj.name)
                if existing is not None and existing is not obj:
                    msg = f"Two providers claim the name {obj.name!r}."
                    raise ProviderRegistrationError(msg)
                found[obj.name] = obj
    return list(found.values())


@lru_cache(maxsize=1)
def providers() -> tuple[InterestProvider, ...]:
    instances = [cls() for cls in _classes()]
    instances.sort(key=lambda p: (p.order, p.name))
    return tuple(instances)


def provider_names() -> tuple[str, ...]:
    return tuple(p.name for p in providers())
