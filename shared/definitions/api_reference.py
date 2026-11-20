"""API reference: its groups, their order and the placeholders of a request example."""

from __future__ import annotations

import json
import shlex
from typing import Any

# name, then path prefixes relative to the api prefix; the longest prefix wins
REFERENCE_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Projects", ("/projects",)),
    ("Targets", ("/targets", "/tags", "/organizations")),
    ("Scans", ("/scans", "/exports")),
    ("Web assets", ("/subdomains", "/http-assets")),
    ("Addresses", ("/ips",)),
    ("Services", ("/ports",)),
    ("Endpoints", ("/endpoints",)),
    ("Findings", ("/vulnerabilities", "/software")),
    ("Compare", ("/scans/compare", "/scans/{id}/comparable")),
    ("Notes", ("/notes",)),
)

GROUP_ORDER: tuple[str, ...] = tuple(name for name, _ in REFERENCE_GROUPS)

EXAMPLE_BASE_URL = "https://rengine.example.com"
EXAMPLE_KEY_VARIABLE = "RENGINE_KEY"
EXAMPLE_VALUE = "…"
# body fields shown in an example when the body requires none
EXAMPLE_FIELDS: tuple[str, ...] = ("q", "queries", "target_ids", "target_values")
METHOD_ORDER: tuple[str, ...] = ("GET", "POST", "PUT", "PATCH", "DELETE")
PROJECT_PARAMETER = "project_id"
# method, path relative to the api prefix, body; shown beside a new key
FIRST_REQUEST: tuple[str, str, dict[str, str]] = (
    "POST",
    "/subdomains/search",
    {"q": "status:200"},
)


def placement(path: str) -> tuple[str, int] | None:
    """The group of a route template relative to the api prefix, and its prefix's rank."""
    best: tuple[int, str, int] | None = None
    for name, prefixes in REFERENCE_GROUPS:
        for rank, prefix in enumerate(prefixes):
            if (path == prefix or path.startswith(f"{prefix}/")) and (
                best is None or len(prefix) > best[0]
            ):
                best = (len(prefix), name, rank)
    return (best[1], best[2]) if best else None


def group_of(path: str) -> str | None:
    found = placement(path)
    return found[0] if found else None


def variable(name: str, before: str = "") -> str:
    """The shell variable a parameter is sent as, `{id}` named after its collection."""
    if name == "id" and before and not before.startswith("{"):
        name = f"{before.removesuffix('s')}_id"
    return f"${name.upper().replace('-', '_')}"


PROJECT_VARIABLE = variable(PROJECT_PARAMETER)


def curl(method: str, path: str, query: list[str], body: Any) -> str:
    """A curl request to the example base URL, path variables as shell variables."""
    pieces = path.split("/")
    for i, piece in enumerate(pieces):
        if piece.startswith("{") and piece.endswith("}"):
            pieces[i] = variable(piece[1:-1], pieces[i - 1] if i else "")
    url = EXAMPLE_BASE_URL + "/".join(pieces)
    if query:
        url = f"{url}?{'&'.join(query)}"
    lines = ["curl" + ("" if method == "GET" else f" -X {method}") + f' "{url}"']
    lines.append(f'-H "Authorization: Bearer ${EXAMPLE_KEY_VARIABLE}"')
    if body is not None:
        lines.append('-H "Content-Type: application/json"')
        lines.append(f"-d {shlex.quote(json.dumps(body, ensure_ascii=False))}")
    return " \\\n  ".join(lines)


def first_request(prefix: str) -> str:
    method, path, body = FIRST_REQUEST
    return curl(
        method, prefix + path, [f"{PROJECT_PARAMETER}={PROJECT_VARIABLE}"], body
    )
