"""One search tool over the five dimensions."""

from __future__ import annotations

from pydantic import Field

from mcp import links
from mcp.context import ToolContext
from mcp.dimensions import DEFAULT_ROWS, DIMENSION_KEYS, MAX_ROWS, dimension
from mcp.errors import ToolError
from mcp.result import ToolResult
from mcp.tools._scope import project_for, resolve
from mcp.tools.base import Tool, ToolGroup, ToolInput
from toolbox.base import cell, hero, table


class Input(ToolInput):
    target: str | None = Field(
        default=None,
        description=(
            "The target to search within. Omit to search every target in the project."
        ),
    )
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
    value_field = "target"
    title = "Query assets"
    group = ToolGroup.INTERROGATE
    description = (
        "Search one dimension of the attack surface with the query language, on one "
        "target or across every target in the project. Returns matching rows and a "
        "total equal to the rows the returned link opens. Rows carry a subset of "
        "columns."
    )
    Input = Input
    examples = (
        "query_assets target=example.com query='is:live and status:200'",
        "query_assets target=example.com dimension=vulnerabilities query='is:kev'",
        "query_assets dimension=vulnerabilities query='severity:critical'",
    )

    async def run(self, ctx: ToolContext, args: Input) -> ToolResult:
        dim = dimension(args.dimension)
        caveats: list[str] = []

        if args.target:
            scope = await resolve(ctx, args.target)
            query_scope = scope.require(dim)
            project_id = scope.project_id
            where = scope.target.target_value
            pivot = links.scan_tab(ctx.ui_base_url, query_scope, dim.tab, args.query)
            caveats.extend(scope.caveat(dim))
        else:
            from app.services.surface_scope import SurfaceScopeService  # noqa: PLC0415

            project_id = await project_for(ctx, None)
            query_scope = await SurfaceScopeService(ctx.session).scope(
                project_id, dim.key
            )
            if not query_scope:
                msg = (
                    f"No settled scan in this project has produced {dim.noun_plural}. "
                    "Report it as not scanned, not as zero."
                )
                raise ToolError(msg)
            where = f"{len(query_scope.ids)} targets"
            pivot = links.surface(ctx.ui_base_url, dim.tab, args.query)

        f = dim.build_filter(args.query, limit=args.limit, offset=args.offset)
        page = await dim.search(ctx.session, query_scope, f, project_id)

        if getattr(page, "error", None):
            raise ToolError(_explain(page.error, args.query or ""))

        rows = [dim.compact(row) for row in page.items]
        total = page.total
        capped = bool(page.total_capped)

        shown = f"showing {len(rows)}" if total > len(rows) else "all shown"
        headline = f"{total}{'+' if capped else ''} {dim.noun_plural} match on {where} ({shown})"

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
            pivot=pivot,
            caveats=caveats,
            untrusted=bool(rows),
            blocks=[
                hero(headline),
                table(
                    [],
                    [
                        [cell(v, mono=i == 0) for i, v in enumerate(_row_cells(row))]
                        for row in rows
                    ],
                    empty=f"No {dim.noun_plural} match.",
                ),
            ],
        )


_ROW_FIELDS = (
    ("severity", "template_name", "template_id", "matched_at", "host", "url"),
    ("host", "name", "status", "title", "ip", "port", "number", "service_name"),
)
_MAX_CELLS = 4
_MAX_CELL = 60


def _row_cells(row: dict) -> list[str]:
    """The few values a phone row can carry, most telling first."""
    out: list[str] = []
    for key in (*_ROW_FIELDS[0], *_ROW_FIELDS[1]):
        value = row.get(key)
        if value in (None, "", [], {}) or (
            key == "template_id" and row.get("template_name")
        ):
            continue
        text = str(value)
        if key in ("matched_at", "url"):
            text = text.split("://", 1)[-1].split("/", 1)[0]
        if text not in out:
            out.append(text[:_MAX_CELL])
        if len(out) >= _MAX_CELLS:
            break
    if not out:
        out = [str(v)[:_MAX_CELL] for v in list(row.values())[:_MAX_CELLS]]
    return out


def _explain(error, query: str) -> str:
    message = getattr(error, "message", None) or "The query could not be parsed."
    hint = getattr(error, "hint", None)
    parts = [f"{message} Query: {query!r}."]
    if hint:
        parts.append(str(hint))
    parts.append("describe_query_language lists the fields this dimension accepts.")
    return " ".join(parts)
