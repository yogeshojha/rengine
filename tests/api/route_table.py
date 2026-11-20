"""The app's routes and their dependencies, read through an included router."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

from fastapi import FastAPI


def routes(app: FastAPI) -> Iterator[Any]:
    """Every route the app serves, each with its full path."""
    for route in app.routes:
        contexts = getattr(route, "effective_route_contexts", None)
        if contexts is None:
            yield route
        else:
            yield from contexts()


def calls(dependant: Any) -> set[Callable[..., Any]]:
    """Every dependency callable under a dependant."""
    found: set[Callable[..., Any]] = set()
    stack = list(dependant.dependencies)
    while stack:
        dependency = stack.pop()
        found.add(dependency.call)
        stack.extend(dependency.dependencies)
    return found
