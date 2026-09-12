"""One search tool over the five dimensions."""

from __future__ import annotations

from pydantic import Field

from mcp import links
from mcp.context import ToolContext
from mcp.dimensions import DEFAULT_ROWS, DIMENSION_KEYS, MAX_ROWS, dimension
from mcp.errors import ToolError
from mcp.result import ToolResult
from mcp.tools._scope import resolve
from mcp.tools.base import Tool, ToolGroup, ToolInput


class Input(ToolInput):
    target: str = Field(description="The target to search within.")
    dimension: str = Field(
        default=DIMENSION_KEYS[0],
        description=f"Which surface to search. One of: {', '.join(DIMENSION_KEYS)}.",
    )
    query: str | None = Field(
        default=None,
        description=(
            "A query, for example `is:live and not is:cdn`, "
            "`severity:critical or is:kev`, `port:22 and is:sensitive`. "
            "describe_query_language lists the fields per dimension. "
            "Omit to return everything in scope."
        ),
    )
    limit: int = Field(
        default=DEFAULT_ROWS, ge=1, le=MAX_ROWS, description="Rows to return."
    )
    offset: int = Field(default=0, ge=0, description="Rows to skip.")


class QueryAssets(Tool):
    name = "query_assets"
    title = "Query assets"
    group = ToolGroup.INTERROGATE.value
    description = (
        "Search one dimension of a target's attack surface with the query language. "
        "Returns matching rows and a total equal to the rows the returned link opens. "
        "Rows carry a subset of columns."
    )
    Input = Input
    examples = (
        "query_assets target=example.com query='is:live and status:200'",
        "query_assets target=example.com dimension=vulnerabilities query='is:kev'",
        "query_assets target=example.com dimension=services query='is:sensitive'",
    )

    async def run(self, ctx: ToolContext, args: Input) -> ToolResult:
        dim = dimension(args.dimension)
        scope = await resolve(ctx, args.target)
        scan_id = scope.require(dim)

        f = dim.build_filter(args.query, limit=args.limit, offset=args.offset)
        page = await dim.search(ctx.session, scan_id, f, scope.project_id)

        if getattr(page, "error", None):
            raise ToolError(_explain(page.error, args.query or ""))

        rows = [dim.compact(row) for row in page.items]
        total = page.total
        capped = bool(page.total_capped)

        shown = f"showing {len(rows)}" if total > len(rows) else "all shown"
        headline = (
            f"{total}{'+' if capped else ''} {dim.noun_plural} match "
            f"on {scope.target.target_value} ({shown})"
        )

        caveats = list(scope.caveat(dim))
        if capped:
            caveats.append(
                f"The total is capped. At least {total} match. "
                "Narrow the query for an exact figure."
            )

        return ToolResult(
            summary=headline,
            data={
                "dimension": dim.key,
                "query": args.query,
                "total": total,
                "total_capped": capped,
                "returned": len(rows),
                "offset": args.offset,
                "rows": rows,
            },
            pivot=links.scan_tab(ctx.ui_base_url, scan_id, dim.tab, args.query),
            caveats=caveats,
            untrusted=bool(rows),
        )


def _explain(error, query: str) -> str:
    message = getattr(error, "message", None) or "The query could not be parsed."
    hint = getattr(error, "hint", None)
    parts = [f"{message} Query: {query!r}."]
    if hint:
        parts.append(str(hint))
    parts.append("describe_query_language lists the fields this dimension accepts.")
    return " ".join(parts)
