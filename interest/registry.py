"""Providers are discovered from disk."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from interest.base import InterestProvider
from shared.plugins import by_name, classes_in_packages

PROVIDER_DIR = Path(__file__).resolve().parent / "providers"


class ProviderRegistrationError(RuntimeError):
    """A provider module is invalid or duplicated."""


def _classes() -> list[type[InterestProvider]]:
    if not PROVIDER_DIR.is_dir():
        return []
    found = classes_in_packages(
        "interest.providers", PROVIDER_DIR, InterestProvider, submodules=("provider",)
    )
    return list(
        by_name(found, kind="provider", error=ProviderRegistrationError).values()
    )


@lru_cache(maxsize=1)
def providers() -> tuple[InterestProvider, ...]:
    instances = [cls() for cls in _classes()]
    instances.sort(key=lambda p: (p.order, p.name))
    return tuple(instances)


def provider_names() -> tuple[str, ...]:
    return tuple(p.name for p in providers())
