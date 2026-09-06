"""Errors an MCP call can raise, and the JSON-RPC codes they map to."""

from __future__ import annotations

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
UNAUTHORIZED = -32001
FORBIDDEN = -32002


class McpError(Exception):
    code = INTERNAL_ERROR

    def __init__(self, message: str, data: dict | None = None):
        super().__init__(message)
        self.message = message
        self.data = data or {}


class ProtocolError(McpError):
    code = INVALID_REQUEST


class MethodNotFoundError(McpError):
    code = METHOD_NOT_FOUND


class InvalidParamsError(McpError):
    code = INVALID_PARAMS


class AuthError(McpError):
    """No usable token on the request."""

    code = UNAUTHORIZED


class CapabilityError(McpError):
    """The token is valid but may not do this."""

    code = FORBIDDEN


class ScopeError(McpError):
    """The token is valid but the resource is outside its project."""

    code = FORBIDDEN


class ToolError(McpError):
    """A tool ran and could not answer. Returned to the model, not to the transport."""

    code = INTERNAL_ERROR
