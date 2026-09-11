"""Tools are discovered by module."""

from __future__ import annotations

import importlib
from functools import lru_cache
from pathlib import Path

from shared.logging import get_logger
from toolbox.base import Tool

logger = get_logger(__name__)

_SKIP = {"__init__"}


@lru_cache(maxsize=1)
def discover() -> dict[str, type[Tool]]:
    found: dict[str, type[Tool]] = {}
    for module in sorted(Path(__file__).parent.glob("*.py")):
        if module.stem in _SKIP or module.stem.startswith("_"):
            continue
        try:
            namespace = importlib.import_module(f"toolbox.tools.{module.stem}")
        except Exception as exc:
            logger.warning("toolbox tool skipped", module=module.stem, error=str(exc))
            continue
        for obj in vars(namespace).values():
            if (
                isinstance(obj, type)
                and issubclass(obj, Tool)
                and obj is not Tool
                and not getattr(obj, "__abstractmethods__", None)
                and getattr(obj, "name", None)
            ):
                found.setdefault(obj.name, obj)
    return found


__all__ = ["discover"]
