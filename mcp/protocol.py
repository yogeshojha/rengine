"""JSON-RPC 2.0 framing and the MCP method names. No transport, no database.

Swapping this module for an SDK later changes nothing above it: `mcp.server`
only depends on `parse`, `success` and `failure`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mcp.errors import INVALID_REQUEST, ProtocolError

VERSION = "2.0"


class Method:
    INITIALIZE = "initialize"
    INITIALIZED = "notifications/initialized"
    PING = "ping"
    TOOLS_LIST = "tools/list"
    TOOLS_CALL = "tools/call"


@dataclass(frozen=True)
class Request:
    id: Any
    method: str
    params: dict

    @property
    def is_notification(self) -> bool:
        return self.id is None


def parse(payload: Any) -> Request:
    if isinstance(payload, list):
        msg = "Batched requests are not supported."
        raise ProtocolError(msg)
    if not isinstance(payload, dict):
        msg = "A request must be a JSON object."
        raise ProtocolError(msg)
    method = payload.get("method")
    if not isinstance(method, str) or not method:
        msg = "A request must carry a method."
        raise ProtocolError(msg)
    params = payload.get("params") or {}
    if not isinstance(params, dict):
        msg = "params must be an object."
        raise ProtocolError(msg)
    return Request(id=payload.get("id"), method=method, params=params)


def success(request_id: Any, result: dict) -> dict:
    return {"jsonrpc": VERSION, "id": request_id, "result": result}


def failure(request_id: Any, code: int, message: str, data: dict | None = None) -> dict:
    error: dict[str, Any] = {"code": code, "message": message}
    if data:
        error["data"] = data
    return {"jsonrpc": VERSION, "id": request_id, "error": error}


def parse_failure(message: str) -> dict:
    return failure(None, INVALID_REQUEST, message)
