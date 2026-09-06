"""One entry point for a whole request: authenticate, gate, dispatch, respond.

The API route calls `handle_request` and nothing else; a stdio entry point would
call the same function. Everything transport-specific stays out of `mcp.server`.
"""

from __future__ import annotations

from typing import Any

from mcp import auth, limits, protocol, server, telemetry
from mcp.context import ToolContext
from mcp.errors import McpError
from mcp.service import McpService
from mcp.settings import HTTP_PATH
from shared.logging import get_logger

logger = get_logger(__name__)

DISABLED_MESSAGE = (
    "The reNgine MCP server is stopped. An operator can start it on the MCP page."
)
RATE_MESSAGE = "Too many calls. Slow down and retry in a minute."


async def handle_request(
    payload: Any,
    *,
    session,
    authorization: str | None,
    ui_base_url: str,
    client_hint: str = "unknown",
) -> dict | None:
    """Answer one JSON-RPC message. None means the caller sent a notification."""
    try:
        request = protocol.parse(payload)
    except McpError as exc:
        return protocol.failure(None, exc.code, exc.message)

    service = McpService(session)

    try:
        config = await service.config()
        if not config.enabled:
            raise _stopped()

        identity, row = await service.authenticate(auth.from_header(authorization))

        if await limits.exceeded(identity.id, config.rate_limit_per_minute):
            from mcp.errors import FORBIDDEN  # noqa: PLC0415

            return protocol.failure(request.id, FORBIDDEN, RATE_MESSAGE)
    except McpError as exc:
        return protocol.failure(request.id, exc.code, exc.message)

    ctx = ToolContext(
        session=session,
        token=identity,
        ui_base_url=ui_base_url,
        client=client_hint,
    )

    response = await server.handle(request, ctx)

    try:
        await service.mark_used(row, ctx.client)
        await telemetry.touch(
            token_id=identity.id,
            token_name=identity.name,
            client=ctx.client,
            capabilities=sorted(identity.capabilities),
            tool=None,
        )
    except Exception as exc:
        logger.debug("mcp bookkeeping skipped", error=str(exc))

    return response


def _stopped() -> McpError:
    from mcp.errors import AuthError  # noqa: PLC0415

    return AuthError(DISABLED_MESSAGE)


__all__ = ["HTTP_PATH", "handle_request"]
