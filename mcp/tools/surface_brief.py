"""Dozens of expert queries, already counted for this scan. The orientation tool."""

from __future__ import annotations

from pydantic import Field

from mcp import links
from mcp.context import ToolContext
from mcp.dimensions import DIMENSION_KEYS, dimension
from mcp.result import ToolResult
from mcp.tools._scope import resolve
from mcp.tools.base import Tool, ToolGroup, ToolInput

MAX_LEADS = 60


class Input(ToolInput):
    target: str = Field(description="The target to brief on.")
    dimension: str = Field(
        default=DIMENSION_KEYS[0],
        description=f"Which surface to brief on. One of: {', '.join(DIMENSION_KEYS)}.",
    )
    include_empty: bool = Field(
        default=False,
        description="Include queries that matched nothing on this scan.",
    )


class SurfaceBrief(Tool):
    name = "surface_brief"
    title = "Surface brief"
    group = ToolGroup.ORIENT.value
    description = (
        "The fastest way to learn what is interesting about a scan. Returns reNgine's "
        "curated query library with a real count against each one for this target, "
        "ranked so the queries that discriminate come first. "
        "Use it before writing your own query — most questions are already here, and "
        "each count is exact."
    )
    Input = Input
    examples = (
        "surface_brief target=example.com",
        "surface_brief target=example.com dimension=vulnerabilities",
    )

    async def run(self, ctx: ToolContext, args: Input) -> ToolResult:
        dim = dimension(args.dimension)
        scope = await resolve(ctx, args.target)
        scan_id = scope.require(dim)

        f = dim.build_filter(None, limit=1, offset=0)
        leads = await dim.leads(ctx.session, scan_id, f, scope.project_id)

        rows = []
        for lead in leads.leads[:MAX_LEADS]:
            if lead.count == 0 and not args.include_empty:
                continue
            rows.append(
                {
                    "query": lead.query,
                    "count": lead.count,
                    "capped": lead.capped,
                    "means": lead.description,
                    "group": lead.group,
                }
            )

        total = leads.total
        hits = [r for r in rows if r["count"]]
        headline = (
            f"{len(hits)} of {len(leads.leads)} standard checks match on "
            f"{scope.target.target_value} — {total} {dim.noun_plural} in scope"
        )

        return ToolResult(
            summary=headline,
            data={
                "dimension": dim.key,
                "scan_id": str(scan_id),
                "total_in_scope": total,
                "total_capped": leads.total_capped,
                "leads": rows,
            },
            pivot=links.scan_tab(ctx.ui_base_url, scan_id, dim.tab),
            caveats=[
                *scope.caveat(dim),
                "Each count was computed with the same filter the UI uses, so it "
                "equals the row count you land on when you run the query.",
            ],
        )
