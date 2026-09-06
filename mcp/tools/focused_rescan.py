"""Re-probe the assets the agent just argued about, as their own run."""

from __future__ import annotations

import uuid

from pydantic import Field

from mcp import links
from mcp.capabilities import Capability
from mcp.context import ToolContext
from mcp.dimensions import DIMENSION_KEYS, dimension
from mcp.errors import ToolError
from mcp.result import ToolResult
from mcp.tools._scope import resolve
from mcp.tools.base import Tool, ToolGroup, ToolInput

MAX_ASSETS = 200


class Input(ToolInput):
    target: str = Field(description="The target the assets belong to.")
    dimension: str = Field(
        description=(f"Which surface to refresh. One of: {', '.join(DIMENSION_KEYS)}.")
    )
    assets: list[str] = Field(
        min_length=1,
        max_length=MAX_ASSETS,
        description=(
            "The exact assets to rescan — hostnames for web assets and endpoints, "
            "IP addresses for services and addresses. Take them from query_assets."
        ),
    )
    stages: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="Stages to run. Omit to use the dimension's defaults.",
    )


class FocusedRescan(Tool):
    name = "focused_rescan"
    title = "Focused rescan"
    capability = Capability.LAUNCH.value
    group = ToolGroup.ACT.value
    description = (
        "Re-run a narrow set of stages against specific assets you have already found, "
        "as its own scan. This is how you check a hypothesis: query, pick the "
        "interesting rows, re-probe just those, then read the result. "
        "It sends traffic to the target. The run is recorded separately and does not "
        "disturb the parent scan's totals."
    )
    Input = Input
    examples = (
        "focused_rescan target=example.com dimension=web_assets "
        "assets=['a.example.com','b.example.com']",
    )

    async def run(self, ctx: ToolContext, args: Input) -> ToolResult:
        from app.services.rescan import RescanService, rescan_schema  # noqa: PLC0415
        from shared.models.scan import RescanCreate  # noqa: PLC0415

        if ctx.token.issued_by is None:
            msg = (
                "This token has no issuing operator, so a rescan cannot be attributed."
            )
            raise ToolError(msg)

        dim = dimension(args.dimension)
        scope = await resolve(ctx, args.target)
        parent_scan_id = scope.require(dim)

        schema = rescan_schema()
        spec = next((d for d in schema.dimensions if d.dimension == dim.key), None)
        if spec is None:
            allowed = ", ".join(d.dimension for d in schema.dimensions)
            msg = f"{dim.label} cannot be rescanned. Try one of: {allowed}."
            raise ToolError(msg)

        unknown = [s for s in args.stages if s not in schema.rescannable_stages]
        if unknown:
            allowed = ", ".join(schema.rescannable_stages)
            msg = f"Not rescannable: {', '.join(unknown)}. Choose from: {allowed}."
            raise ToolError(msg)

        assets = [a.strip() for a in args.assets if a and a.strip()]
        if len(assets) > schema.max_assets:
            msg = f"At most {schema.max_assets} assets per rescan."
            raise ToolError(msg)

        try:
            data = RescanCreate.model_validate(
                {
                    "parent_scan_id": parent_scan_id,
                    "dimension": dim.key,
                    "assets": assets,
                    "stages": args.stages or list(spec.default_stages),
                }
            )
            scan = await RescanService(ctx.session).create(
                data=data,
                project_id=scope.project_id,
                created_by=ctx.token.issued_by,
            )
        except Exception as exc:
            msg = f"The rescan could not be started: {exc}"
            raise ToolError(msg) from exc

        stages = args.stages or list(spec.default_stages)
        return ToolResult(
            summary=(
                f"Rescanning {len(assets)} {spec.noun_plural} on "
                f"{scope.target.target_value} with {', '.join(stages)}"
            ),
            data={
                "scan_id": str(scan.id),
                "parent_scan_id": str(parent_scan_id),
                "dimension": dim.key,
                "assets": len(assets),
                "stages": stages,
                "status": scan.status,
            },
            pivot=links.scan(ctx.ui_base_url, scan.id),
            caveats=[
                "Traffic is now being sent to these assets.",
                "Results land on this run, not on the parent scan's totals.",
            ],
        )


def _uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        msg = "Expected a UUID."
        raise ToolError(msg) from exc
