from __future__ import annotations

import uuid

import pytest

from mcp import server, telemetry
from mcp.context import TokenIdentity, ToolContext
from mcp.errors import ToolError

pytestmark = pytest.mark.api


async def test_an_unknown_tool_name_is_clipped_in_the_log_and_the_error(monkeypatch):
    recorded: list[telemetry.CallRecord] = []

    async def record(call):
        recorded.append(call)

    async def touch(**_kwargs):
        return None

    monkeypatch.setattr(telemetry, "record", record)
    monkeypatch.setattr(telemetry, "touch", touch)
    token = TokenIdentity(
        id=uuid.uuid4(), name="agent", project_id=None, capabilities=frozenset()
    )
    ctx = ToolContext(session=None, token=token, ui_base_url="", client="http")
    name = "x" * 100_000

    with pytest.raises(ToolError) as raised:
        await server.invoke(ctx, name, {})

    assert len(recorded) == 1
    assert len(recorded[0].tool) <= telemetry.TOOL_NAME_MAX
    assert name not in raised.value.message
    assert "x" * (telemetry.TOOL_NAME_MAX + 1) not in raised.value.message
