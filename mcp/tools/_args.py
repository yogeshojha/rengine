"""Argument parsing shared by tools, with errors written for the model."""

from __future__ import annotations

import uuid

from mcp.errors import ToolError


def parse_uuid(value: str, field: str) -> uuid.UUID:
    """The id in `value`, or a `ToolError` naming the argument that held it."""
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        msg = f"{field} must be a uuid, not {value!r}."
        raise ToolError(msg) from exc


def optional_uuid(value: str | None, field: str) -> uuid.UUID | None:
    """Like `parse_uuid`, with an empty or missing argument meaning no id."""
    return parse_uuid(value, field) if value else None
