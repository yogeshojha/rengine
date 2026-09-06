"""Every discovered tool, validated once and described for the wire and the UI."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from mcp.capabilities import CAPABILITY_ORDER
from mcp.tools import Tool, discover


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
                "readOnlyHint": self.capability == CAPABILITY_ORDER[0],
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


@lru_cache(maxsize=1)
def registry() -> dict[str, ToolSpec]:
    specs: dict[str, ToolSpec] = {}
    for name, cls in sorted(discover().items()):
        _validate(cls)
        specs[name] = ToolSpec(
            name=name,
            title=cls.title,
            description=cls.description.strip(),
            capability=cls.capability,
            group=cls.group,
            destructive=bool(cls.destructive),
            examples=tuple(cls.examples),
            tool_cls=cls,
        )
    return specs


def specs_for(capabilities: frozenset[str] | set[str]) -> list[ToolSpec]:
    return [s for s in registry().values() if s.capability in capabilities]


def get(name: str) -> ToolSpec | None:
    return registry().get(name)
