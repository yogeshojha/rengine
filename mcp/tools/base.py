"""The Tool contract. Subclass it, drop the file in this directory, and it is live.

    class Ping(Tool):
        name = "ping_example"
        title = "Ping"
        description = "Answers with pong."

        class Input(ToolInput):
            loudly: bool = Field(default=False, description="Shout it")

        async def run(self, ctx, args):
            return ToolResult(summary="pong!" if args.loudly else "pong")

Nothing else registers it: `mcp.registry` discovers every Tool subclass under
`mcp/tools/`, turns `Input` into the JSON Schema the model sees, and gates the
call on `capability`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import ClassVar

from pydantic import BaseModel, ConfigDict

from mcp.capabilities import Capability
from mcp.context import ToolContext
from mcp.result import ToolResult


class ToolInput(BaseModel):
    """Base for a tool's arguments. Field(description=...) is what the model reads."""

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
    Input: ClassVar[type[ToolInput]] = NoInput
    # shown in the UI and the docs, never sent to the model
    examples: ClassVar[tuple[str, ...]] = ()

    @abstractmethod
    async def run(self, ctx: ToolContext, args: ToolInput) -> ToolResult:
        """Answer the call. Raise ToolError for anything the caller should see."""

    @classmethod
    def schema(cls) -> dict:
        schema = cls.Input.model_json_schema()
        schema.pop("title", None)
        schema.setdefault("type", "object")
        schema.setdefault("properties", {})
        return schema
