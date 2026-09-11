"""The Tool contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import ClassVar

from pydantic import BaseModel, ConfigDict

from mcp.capabilities import Capability
from mcp.context import ToolContext
from mcp.result import ToolResult


class ToolInput(BaseModel):
    """Base for a tool's arguments."""

    model_config = ConfigDict(extra="forbid")


class NoInput(ToolInput):
    pass


class ToolGroup(StrEnum):
    ORIENT = "Orient"
    INTERROGATE = "Interrogate"
    EXPLAIN = "Explain"
    ACT = "Act"


class Tool(ABC):
    """One callable an agent can invoke."""

    name: ClassVar[str]
    title: ClassVar[str]
    description: ClassVar[str]
    capability: ClassVar[str] = Capability.READ.value
    group: ClassVar[str] = ToolGroup.INTERROGATE.value
    # the call destroys data a user cannot get back
    destructive: ClassVar[bool] = False
    Input: ClassVar[type[ToolInput]] = NoInput
    examples: ClassVar[tuple[str, ...]] = ()

    @abstractmethod
    async def run(self, ctx: ToolContext, args: ToolInput) -> ToolResult:
        """Answer the call."""

    @classmethod
    def schema(cls) -> dict:
        schema = cls.Input.model_json_schema()
        schema.pop("title", None)
        schema.setdefault("type", "object")
        schema.setdefault("properties", {})
        return schema
