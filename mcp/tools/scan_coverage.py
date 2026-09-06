"""What actually ran. The tool that keeps "no findings" honest."""

from __future__ import annotations

from pydantic import Field

from mcp import links
from mcp.context import ToolContext
from mcp.dimensions import DIMENSIONS, dimension
from mcp.result import ToolResult
from mcp.tools._scope import resolve
from mcp.tools.base import Tool, ToolGroup, ToolInput
from shared.definitions.surface import SurfaceDimension

_COVERAGE_DIMENSIONS = (
    SurfaceDimension.VULNERABILITIES.value,
    SurfaceDimension.ENDPOINTS.value,
)


class Input(ToolInput):
    target: str = Field(description="The target to report coverage for.")
    dimension: str = Field(
        default=SurfaceDimension.VULNERABILITIES.value,
        description=(
            f"Which run to account for. One of: {', '.join(_COVERAGE_DIMENSIONS)}."
        ),
    )


class ScanCoverage(Tool):
    name = "scan_coverage"
    title = "Scan coverage"
    group = ToolGroup.EXPLAIN.value
    description = (
        "The scanner's own account of a run: checks selected against checks actually "
        "loaded, hosts scanned, requests sent, errors, and hosts it gave up on. "
        "Call this before reporting that something found nothing — a null count means "
        "the scanner did not report that number, never that it was zero."
    )
    Input = Input
    examples = ("scan_coverage target=example.com",)

    async def run(self, ctx: ToolContext, args: Input) -> ToolResult:
        dim = dimension(args.dimension)
        scope = await resolve(ctx, args.target)
        scan_id = scope.require(dim)

        service = dim.service(ctx.session)
        rows = await service.coverage(scan_id)

        runs = [
            {
                k: v
                for k, v in row.model_dump(mode="json").items()
                if v not in (None, [], {}, "")
            }
            for row in rows
        ]
        partial = [r for r in runs if r.get("status") not in ("completed", None)]

        summary_line = f"{len(runs)} run(s) recorded for {dim.label}"
        if partial:
            summary_line += f", {len(partial)} did not complete cleanly"

        caveats = list(scope.caveat(dim))
        caveats.append(
            "A count reported as null means the scanner did not say, not zero."
        )
        if not runs:
            caveats.append(
                "No coverage rows exist, so nothing can be said about what ran."
            )

        return ToolResult(
            summary=summary_line,
            data={
                "dimension": dim.key,
                "scan_id": str(scan_id),
                "runs": runs,
                "surface": [
                    {
                        "dimension": d.key,
                        "covered": scope.coverage(d.key).covered,
                        "count": scope.coverage(d.key).value,
                    }
                    for d in DIMENSIONS
                ],
            },
            pivot=links.scan_tab(ctx.ui_base_url, scan_id, dim.tab),
            caveats=caveats,
        )
