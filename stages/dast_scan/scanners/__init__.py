"""Fuzzers, discovered by module."""

from __future__ import annotations

import contextlib
import importlib
from functools import lru_cache
from pathlib import Path

from stages.vulnerability_scan.scanners.base import VulnScanner


@lru_cache(maxsize=1)
def scanners() -> dict[str, type[VulnScanner]]:
    found: dict[str, type[VulnScanner]] = {}
    for module in sorted(Path(__file__).parent.glob("*.py")):
        if module.stem == "__init__":
            continue
        with contextlib.suppress(ModuleNotFoundError):
            namespace = importlib.import_module(
                f"stages.dast_scan.scanners.{module.stem}"
            )
            for obj in vars(namespace).values():
                if (
                    isinstance(obj, type)
                    and issubclass(obj, VulnScanner)
                    and obj is not VulnScanner
                    and getattr(obj, "name", None)
                    and obj.__module__ == namespace.__name__
                ):
                    found.setdefault(obj.name, obj)
    return found


__all__ = ["scanners"]
