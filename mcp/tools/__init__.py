"""Tools are discovered by module."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from mcp.tools.base import Tool
from shared.plugins import classes_in_modules


@lru_cache(maxsize=1)
def discover() -> dict[str, type[Tool]]:
    found: dict[str, type[Tool]] = {}
    for cls in classes_in_modules("mcp.tools", Path(__file__).parent, Tool):
        if cls.name:
            found.setdefault(cls.name, cls)
    return found


__all__ = ["Tool", "discover"]
