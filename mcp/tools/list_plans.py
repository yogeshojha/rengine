"""The saved configurations start_scan takes ids for. Without these they are unusable."""

from __future__ import annotations

import uuid

from pydantic import Field

from mcp.context import ToolContext
from mcp.errors import ToolError
from mcp.result import ToolResult
from mcp.tools._scope import project_for
from mcp.tools.base import Tool, ToolGroup, ToolInput

MAX_ROWS = 50


class EnginesInput(ToolInput):
    contains: str | None = Field(
        default=None,
        description="Only engines whose name or description contains this text.",
    )
    project_id: str | None = Field(
        default=None,
        description="Which project's engines. Omit when the token is scoped to one.",
    )
    limit: int = Field(default=25, ge=1, le=MAX_ROWS)


class ListEngines(Tool):
    name = "list_engines"
    title = "List scan engines"
    group = ToolGroup.ORIENT.value
    description = (
        "The saved scan engines in a project, with the id start_scan and plan_scan "
        "take. An engine is a stored configuration of stages — what a person set up "
        "and named. Call this before starting a scan so you can run the operator's "
        "own configuration instead of assembling stages yourself, and quote the "
        "engine by name when you say what you are about to run."
    )
    Input = EnginesInput
    examples = ("list_engines", "list_engines contains=passive")

    async def run(self, ctx: ToolContext, args: EnginesInput) -> ToolResult:
        from app.services.scan_engine import ScanEngineService  # noqa: PLC0415

        project_id = await project_for(ctx, _uuid(args.project_id, "project_id"))
        rows = await ScanEngineService(ctx.session).list(project_id)
        if args.contains:
            needle = args.contains.strip().lower()
            rows = [
                row
                for row in rows
                if needle in row.name.lower()
                or needle in (row.description or "").lower()
            ]

        shown = rows[: args.limit]
        return ToolResult(
            summary=f"{len(rows)} scan engine(s) in this project",
            data=[
                {
                    "id": str(row.id),
                    "name": row.name,
                    "description": row.description,
                    "intensity": row.intensity,
                    "stages": sorted(
                        name
                        for name, cfg in (row.stages or {}).items()
                        if cfg.get("enabled", True)
                    ),
                    "last_used_at": row.last_used_at,
                }
                for row in shown
            ],
            pivot=f"{ctx.ui_base_url.rstrip('/')}/engines",
            caveats=[
                *_more(len(rows), len(shown), "engines"),
                "`stages` is only what each engine's document names. A stage it omits still runs at that stage's own default, so an empty list does not mean an empty scan — use plan_scan to resolve what a run would actually do.",
            ],
        )


class ContextsInput(ToolInput):
    project_id: str | None = Field(
        default=None,
        description="Which project's contexts. Omit when the token is scoped to one.",
    )
    limit: int = Field(default=25, ge=1, le=MAX_ROWS)


class ListContexts(Tool):
    name = "list_contexts"
    title = "List scan contexts"
    group = ToolGroup.ORIENT.value
    description = (
        "The saved scan contexts in a project, with the id start_scan takes. A context "
        "carries how to reach a target: authentication, what is in and out of scope, "
        "rate limits, proxy. Pass one when scanning something that needs a login or "
        "must stay inside an agreed scope. Credentials are never returned — only a "
        "description of what each context holds."
    )
    Input = ContextsInput
    examples = ("list_contexts",)

    async def run(self, ctx: ToolContext, args: ContextsInput) -> ToolResult:
        from app.services.scan_context import ScanContextService  # noqa: PLC0415

        project_id = await project_for(ctx, _uuid(args.project_id, "project_id"))
        rows = await ScanContextService(ctx.session).list(project_id)
        shown = rows[: args.limit]
        return ToolResult(
            summary=f"{len(rows)} scan context(s) in this project",
            data=[
                {
                    "id": str(row.id),
                    "name": row.name,
                    "description": row.description,
                    "auth": row.auth_summary,
                    "rate_limit_per_minute": row.global_rate_limit_override,
                    "excluded": {
                        "hosts": row.excluded_subdomains,
                        "paths": row.excluded_paths,
                        "addresses": row.excluded_ips,
                    },
                    "only_these_hosts": row.included_subdomains,
                    "through_proxy": row.proxy_id is not None,
                    "last_used_at": row.last_used_at,
                }
                for row in shown
            ],
            pivot=f"{ctx.ui_base_url.rstrip('/')}/automation/contexts",
            caveats=[
                *_more(len(rows), len(shown), "contexts"),
                "Credentials are held encrypted and are never returned by this server.",
            ],
        )


def _more(total: int, shown: int, noun: str) -> list[str]:
    return (
        [f"{total - shown} more {noun} not shown; raise `limit`."]
        if total > shown
        else []
    )


def _uuid(value: str | None, field: str) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        msg = f"{field} must be a uuid, not {value!r}."
        raise ToolError(msg) from exc
