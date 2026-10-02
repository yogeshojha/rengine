"""The read-only tools the agent may call, and how a result reaches it."""

from __future__ import annotations

import json
import time
from typing import Any

from mcp import registry, server, telemetry
from mcp.capabilities import Capability
from mcp.context import TokenIdentity, ToolContext
from mcp.errors import McpError
from shared.definitions.ask import ASK_CLIENT, TOOL_TEXT_CHARS, TraceStatus
from shared.definitions.surface import SurfaceDimension
from shared.models.ask import TraceStep
from shared.models.user import User
from shared.services.ai.agent import AgentTool
from shared.services.issue_tracking.body import mask_secrets
from shared.services.scan_resolve import redact_credentials

EXCLUDED = frozenset({"list_projects"})
ROW_TOOLS = frozenset({"query_assets", "compare_runs"})
VALUE_GROUP = ("group_assets", "value")
COUNT_KEYS = ("total", "count", "occurrences", "matched")
MAX_DETAIL = 200
TOOL_BROKE = "The tool did not complete."
SECRETS_REFUSED = "Secret values are not read through Ask."


def identity_for(user: User, project_id: Any) -> TokenIdentity:
    return TokenIdentity(
        id=user.id,
        name=ASK_CLIENT,
        project_id=project_id,
        capabilities=frozenset({Capability.READ.value}),
        issued_by=user.id,
    )


def agent_tools() -> list[AgentTool]:
    return [
        AgentTool(spec.name, spec.description, spec.schema)
        for spec in registry.specs_for({Capability.READ.value})
        if spec.name not in EXCLUDED
    ]


def label(name: str) -> str:
    spec = registry.get(name)
    return spec.title if spec else name


def rows_in(data: Any) -> int | None:
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for key in COUNT_KEYS:
            if isinstance(data.get(key), int):
                return data[key]
        for value in data.values():
            if isinstance(value, list):
                return len(value)
    return None


def reads_secrets(name: str, args: dict) -> bool:
    if args.get("dimension") != SurfaceDimension.SECRETS.value:
        return False
    return name in ROW_TOOLS or (name, args.get("group_by")) == VALUE_GROUP


def scrub(value: Any) -> Any:
    """Mask every string leaf of a tool payload."""
    if isinstance(value, str):
        return mask_secrets(redact_credentials(value))
    if isinstance(value, list):
        return [scrub(v) for v in value]
    if isinstance(value, dict):
        return {k: scrub(v) for k, v in value.items()}
    return value


def _text(payload: dict) -> str:
    text = json.dumps(scrub(payload), indent=2, default=str)
    if len(text) > TOOL_TEXT_CHARS:
        text = f"{text[:TOOL_TEXT_CHARS]}\nTruncated."
    return text


def _failed(name: str, started: float, detail: str, args: dict) -> TraceStep:
    return TraceStep(
        tool=name,
        label=label(name),
        status=TraceStatus.FAILED.value,
        ms=int((time.monotonic() - started) * 1000),
        detail=detail[:MAX_DETAIL],
        args=telemetry.phrase_args(args),
    )


async def call(ctx: ToolContext, name: str, args: dict) -> tuple[str, TraceStep]:
    started = time.monotonic()
    if reads_secrets(name, args):
        return SECRETS_REFUSED, _failed(name, started, SECRETS_REFUSED, args)
    try:
        result = await server.invoke(ctx, name, args)
    except McpError as exc:
        return exc.message, _failed(name, started, exc.message, args)
    except Exception as exc:
        await ctx.session.rollback()
        return TOOL_BROKE, _failed(name, started, str(exc), args)
    return _text(result.payload()), TraceStep(
        tool=name,
        label=label(name),
        status=TraceStatus.DONE.value,
        rows=rows_in(result.data),
        pivot=result.pivot,
        ms=int((time.monotonic() - started) * 1000),
        args=telemetry.phrase_args(args),
    )
