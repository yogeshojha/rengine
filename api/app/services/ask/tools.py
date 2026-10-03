"""The read-only tools the agent may call, and how a result reaches it."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from app.services.ask.verdict import hides_values
from mcp import registry, server, telemetry
from mcp.capabilities import Capability
from mcp.context import TokenIdentity, ToolContext
from mcp.errors import McpError
from shared.definitions.ask import ASK_CLIENT, TOOL_TEXT_CHARS, TraceStatus
from shared.definitions.compare import WATCHED_FIELDS
from shared.definitions.surface import SurfaceDimension
from shared.models.ask import TraceStep
from shared.models.user import User
from shared.services.ai.agent import AgentTool
from shared.services.issue_tracking.body import mask_secrets
from shared.services.scan_resolve import MASK, redact_credentials

EXCLUDED = frozenset({"list_projects"})
ROW_TOOLS = frozenset({"query_assets", "compare_runs"})
VALUE_GROUP = ("group_assets", "value")
EXPLAIN_TOOL = "explain_finding"
COMPARE_TOOL = "compare_runs"
EXTRACTED_FIELD = "extracted_results"
COUNT_KEYS = ("total", "count", "occurrences", "matched")
MAX_DETAIL = 200
SECRETS_REFUSED = "Secret values are not read through Ask."
NOT_OFFERED = "The tool is not available in Ask."
NO_THREAD = "The tool call is not tied to an Ask thread."


def identity_for(
    user: User, project_id: Any, target_id: uuid.UUID | None = None
) -> TokenIdentity:
    return TokenIdentity(
        id=user.id,
        name=ASK_CLIENT,
        project_id=project_id,
        capabilities=frozenset({Capability.READ.value}),
        issued_by=user.id,
        targets=frozenset({target_id}) if target_id else None,
    )


def offered() -> list[registry.ToolSpec]:
    return [
        spec
        for spec in registry.specs_for({Capability.READ.value})
        if spec.name not in EXCLUDED
    ]


def agent_tools() -> list[AgentTool]:
    return [AgentTool(spec.name, spec.description, spec.schema) for spec in offered()]


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


def _extracted_label() -> str:
    fields = WATCHED_FIELDS[SurfaceDimension.VULNERABILITIES.value]
    return next(f.label for f in fields if f.name == EXTRACTED_FIELD)


def hide_extracted(name: str, payload: dict) -> dict:
    """Replace extracted values a credential check found, and every compared one."""
    data = payload.get("data")
    if not isinstance(data, dict):
        return payload
    if name == EXPLAIN_TOOL:
        check = data.get("check") or {}
        evidence = data.get("evidence") or {}
        shown = evidence.get("extracted")
        if shown and hides_values(
            str(check.get("template_id") or ""), check.get("tags") or []
        ):
            evidence["extracted"] = [MASK for _ in shown]
    elif name == COMPARE_TOOL:
        extracted = _extracted_label()
        for change in data.get("changes") or []:
            for field in change.get("fields") or []:
                if field.get("field") != extracted:
                    continue
                for side in ("was", "now"):
                    if field.get(side):
                        field[side] = MASK
    return payload


def _text(name: str, payload: dict) -> str:
    text = json.dumps(hide_extracted(name, scrub(payload)), indent=2, default=str)
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
    if name not in {spec.name for spec in offered()}:
        return NOT_OFFERED, _failed(name, started, NOT_OFFERED, args)
    if reads_secrets(name, args):
        return SECRETS_REFUSED, _failed(name, started, SECRETS_REFUSED, args)
    if ctx.token.targets is None:
        return NO_THREAD, _failed(name, started, NO_THREAD, args)
    try:
        result = await server.invoke(ctx, name, args)
    except McpError as exc:
        return exc.message, _failed(name, started, exc.message, args)
    except Exception as exc:
        await ctx.session.rollback()
        message = server.failed(label(name), exc)
        return message, _failed(name, started, message, args)
    return _text(name, result.payload()), TraceStep(
        tool=name,
        label=label(name),
        status=TraceStatus.DONE.value,
        rows=rows_in(result.data),
        pivot=result.pivot,
        ms=int((time.monotonic() - started) * 1000),
        args=telemetry.phrase_args(args),
    )
