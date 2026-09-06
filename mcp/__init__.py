"""reNgine's Model Context Protocol server.

Everything MCP lives in this package: the wire protocol, the tool registry, the
default tools, tokens and settings. The API exposes it through one thin route
file; nothing outside imports a submodule directly except `mcp.service` and
`mcp.transport`.

Adding a tool is one file in `mcp/tools/`. See ADDING_A_TOOL.md.
"""

from __future__ import annotations

from mcp.capabilities import Capability
from mcp.context import TokenIdentity, ToolContext
from mcp.result import ToolResult
from mcp.tools.base import Tool, ToolGroup, ToolInput

__all__ = [
    "Capability",
    "TokenIdentity",
    "Tool",
    "ToolContext",
    "ToolGroup",
    "ToolInput",
    "ToolResult",
]
