"""stdio transport, for an agent that launches the server itself.

    docker compose exec -T api python -m mcp.stdio

Reads one JSON-RPC message per line on stdin, writes one per line on stdout.
The token comes from RENGINE_MCP_TOKEN — the same token the HTTP transport takes,
so nothing about permissions changes with the transport.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import sys

from mcp.protocol import parse_failure
from mcp.transport import handle_request

TOKEN_VAR = "RENGINE_MCP_TOKEN"  # noqa: S105
UI_VAR = "RENGINE_UI_URL"
DEFAULT_UI = "http://localhost:5173"


async def _serve() -> None:
    from app.core.database import async_db_session  # noqa: PLC0415

    token = os.environ.get(TOKEN_VAR, "").strip()
    ui_base = os.environ.get(UI_VAR, DEFAULT_UI)
    loop = asyncio.get_running_loop()

    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line:
            return
        line = line.strip()
        if not line:
            continue

        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            _emit(parse_failure("That is not valid JSON."))
            continue

        async with async_db_session() as session:
            response = await handle_request(
                payload,
                session=session,
                authorization=token,
                ui_base_url=ui_base,
                client_hint="stdio",
            )
        if response is not None:
            _emit(response)


def _emit(message: dict) -> None:
    sys.stdout.write(json.dumps(message) + "\n")
    sys.stdout.flush()


def main() -> None:
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(_serve())


if __name__ == "__main__":
    main()
