"""Every discovered tool, validated once and described for the wire and the UI."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from mcp.capabilities import CAPABILITY_ORDER, Capability
from mcp.tools import Tool, ToolGroup, discover

COMMAND_RE = re.compile(r"^[a-z][a-z0-9]{1,15}$")


class ToolRegistrationError(RuntimeError):
    """A tool module declares an invalid tool."""


@dataclass(frozen=True)
class ToolSpec:
    name: str
    title: str
    description: str
    capability: str
    group: str
    destructive: bool
    command: str | None
    value_field: str
    examples: tuple[str, ...]
    tool_cls: type[Tool]

    @property
    def schema(self) -> dict:
        return self.tool_cls.schema()

    def descriptor(self) -> dict:
        """The shape an MCP client receives from tools/list."""
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "inputSchema": self.schema,
            "annotations": {
                "readOnlyHint": self.capability == Capability.READ.value,
                "destructiveHint": self.destructive,
            },
        }


def _validate(cls: type[Tool]) -> None:
    for attribute in ("name", "title", "description"):
        if not getattr(cls, attribute, None):
            msg = f"{cls.__qualname__} must set `{attribute}`."
            raise ToolRegistrationError(msg)
    if cls.capability not in CAPABILITY_ORDER:
        msg = f"{cls.__qualname__} declares unknown capability {cls.capability!r}."
        raise ToolRegistrationError(msg)
    if cls.group not in set(ToolGroup):
        msg = f"{cls.__qualname__} declares unknown group {cls.group!r}."
        raise ToolRegistrationError(msg)
    if cls.command is not None and not COMMAND_RE.match(cls.command):
        msg = f"{cls.__qualname__} declares an invalid command {cls.command!r}."
        raise ToolRegistrationError(msg)
    if cls.value_field and cls.value_field not in cls.Input.model_fields:
        msg = f"{cls.__qualname__}.value_field names no field of its Input."
        raise ToolRegistrationError(msg)


@lru_cache(maxsize=1)
def registry() -> dict[str, ToolSpec]:
    specs: dict[str, ToolSpec] = {}
    commands: dict[str, str] = {}
    for name, cls in sorted(discover().items()):
        _validate(cls)
        command = cls.command
        if command is not None:
            if command in commands:
                msg = f"{name} and {commands[command]} both answer to /{command}."
                raise ToolRegistrationError(msg)
            commands[command] = name
        specs[name] = ToolSpec(
            name=name,
            title=cls.title,
            description=cls.description.strip(),
            # plain strings from here on: the wire, the UI and the ceiling key on them
            capability=Capability(cls.capability).value,
            group=ToolGroup(cls.group).value,
            destructive=bool(cls.destructive),
            command=command,
            value_field=cls.value_field,
            examples=tuple(cls.examples),
            tool_cls=cls,
        )
    return specs


def specs_for(capabilities: frozenset[str] | set[str]) -> list[ToolSpec]:
    return [s for s in registry().values() if s.capability in capabilities]


def get(name: str) -> ToolSpec | None:
    return registry().get(name)
