"""Aggregate a dimension by any of its group keys. Each group carries its own query."""

from __future__ import annotations

from pydantic import Field

from mcp import links
from mcp.context import ToolContext
from mcp.dimensions import DIMENSION_KEYS, dimension
from mcp.errors import ToolError
from mcp.result import ToolResult
from mcp.tools._scope import resolve
from mcp.tools.base import Tool, ToolGroup, ToolInput

MAX_GROUPS = 40


class Input(ToolInput):
    target: str = Field(description="The target to aggregate.")
    dimension: str = Field(
        default=DIMENSION_KEYS[0],
        description=f"Which surface to aggregate. One of: {', '.join(DIMENSION_KEYS)}.",
    )
    group_by: str = Field(
        description=(
            "The grouping key. describe_query_language lists the keys each "
            "dimension supports, for example tech, status, asn, country, severity."
        )
    )
    query: str | None = Field(
        default=None, description="Optional query to aggregate within."
    )


class GroupAssets(Tool):
    name = "group_assets"
    title = "Group assets"
    group = ToolGroup.INTERROGATE.value
    description = (
        "Count a target's surface by a dimension — technology, status, ASN, country, "
        "severity, service class and so on. Every group comes back with the query "
        "that isolates it, so you can drill straight in and the count will match."
    )
    Input = Input
    examples = (
        "group_assets target=example.com group_by=tech",
        "group_assets target=example.com dimension=vulnerabilities group_by=severity",
    )

    async def run(self, ctx: ToolContext, args: Input) -> ToolResult:
        dim = dimension(args.dimension)
        scope = await resolve(ctx, args.target)
        scan_id = scope.require(dim)

        keys = [d.key for d in dim.registry.dimensions]
        if args.group_by not in keys:
            msg = (
                f"{dim.label} cannot be grouped by {args.group_by!r}. "
                f"Try one of: {', '.join(keys)}."
            )
            raise ToolError(msg)

        f = dim.build_filter(args.query, limit=1, offset=0)
        result = await dim.groups(
            ctx.session, scan_id, f, args.group_by, scope.project_id
        )

        groups = [
            {"value": g.label or g.value, "count": g.count, "query": g.query}
            for g in result.groups[:MAX_GROUPS]
        ]
        label = next(
            (d.label for d in dim.registry.dimensions if d.key == args.group_by),
            args.group_by,
        )

        caveats = list(scope.caveat(dim))
        if result.truncated:
            caveats.append(
                f"{result.total_groups} groups exist; the largest {len(groups)} are shown."
            )
        if result.covered < result.rows:
            caveats.append(
                f"{result.rows - result.covered} of {result.rows} "
                f"{dim.noun_plural} have no value for this key."
            )

        return ToolResult(
            summary=(
                f"{result.total_groups} distinct {label.lower()} values across "
                f"{result.rows} {dim.noun_plural} on {scope.target.target_value}"
            ),
            data={
                "dimension": dim.key,
                "group_by": args.group_by,
                "rows_in_scope": result.rows,
                "rows_with_a_value": result.covered,
                "total_groups": result.total_groups,
                "groups": groups,
            },
            pivot=links.scan_tab(ctx.ui_base_url, scan_id, dim.tab, args.query),
            caveats=caveats,
            untrusted=True,
        )
