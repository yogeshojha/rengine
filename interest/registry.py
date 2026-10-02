"""Providers are discovered from disk."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from interest.base import InterestProvider
from shared.plugins import classes_in_packages

PROVIDER_DIR = Path(__file__).resolve().parent / "providers"


class ProviderRegistrationError(RuntimeError):
    """A provider module is invalid or duplicated."""


def _classes() -> list[type[InterestProvider]]:
    found: dict[str, type[InterestProvider]] = {}
    for obj in classes_in_packages(
        "interest.providers", PROVIDER_DIR, InterestProvider, submodules=("provider",)
    ):
        if not obj.name:
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
