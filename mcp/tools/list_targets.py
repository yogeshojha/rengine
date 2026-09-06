"""What this token can see. The tool an agent reaches for when nothing is named."""

from __future__ import annotations

from pydantic import Field
from sqlmodel import select

from mcp import links
from mcp.context import ToolContext
from mcp.result import ToolResult
from mcp.tools.base import Tool, ToolGroup, ToolInput
from shared.models.project import Project
from shared.models.target import Target

MAX_TARGETS = 100


class Input(ToolInput):
    contains: str | None = Field(
        default=None, description="Only targets whose value contains this text."
    )
    limit: int = Field(default=50, ge=1, le=MAX_TARGETS)


class ListTargets(Tool):
    name = "list_targets"
    title = "List targets"
    group = ToolGroup.ORIENT.value
    description = (
        "The targets this token can reach, with their project and type. "
        "Use it when the user names something loosely, or to check what exists before "
        "resolving a target."
    )
    Input = Input
    examples = ("list_targets", "list_targets contains=acme")

    async def run(self, ctx: ToolContext, args: Input) -> ToolResult:
        statement = select(Target)
        scoped = ctx.scoped_projects()
        if scoped is not None:
            statement = statement.where(Target.project_id.in_(scoped))
        if args.contains:
            statement = statement.where(
                Target.target_value.ilike(f"%{args.contains.strip()}%")
            )

        rows = (
            (await ctx.session.execute(statement.order_by(Target.target_value)))
            .scalars()
            .all()
        )
        projects = {
            p.id: p.name
            for p in (await ctx.session.execute(select(Project))).scalars().all()
        }

        shown = rows[: args.limit]
        return ToolResult(
            summary=f"{len(rows)} target(s) in scope",
            data={
                "scope": "all projects"
                if ctx.token.project_id is None
                else projects.get(ctx.token.project_id, str(ctx.token.project_id)),
                "total": len(rows),
                "targets": [
                    {
                        "value": row.target_value,
                        "type": getattr(row.target_type, "value", str(row.target_type)),
                        "project": projects.get(row.project_id),
                        "added_at": row.created_at,
                    }
                    for row in shown
                ],
            },
            pivot=f"{ctx.ui_base_url.rstrip('/')}/targets",
            caveats=(
                [f"{len(rows) - len(shown)} more not shown; narrow with `contains`."]
                if len(rows) > len(shown)
                else []
            ),
        )


class ListProjects(Tool):
    name = "list_projects"
    title = "List projects"
    group = ToolGroup.ORIENT.value
    description = "The projects this token can reach."
    examples = ("list_projects",)

    async def run(self, ctx: ToolContext, args: ToolInput) -> ToolResult:  # noqa: ARG002
        rows = (await ctx.session.execute(select(Project))).scalars().all()
        scoped = ctx.scoped_projects()
        visible = [r for r in rows if scoped is None or r.id in scoped]
        return ToolResult(
            summary=f"{len(visible)} project(s) in scope",
            data=[{"id": str(r.id), "name": r.name, "slug": r.slug} for r in visible],
            pivot=links.dashboard(ctx.ui_base_url),
        )
