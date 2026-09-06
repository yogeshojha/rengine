"""An agent's judgement, made durable. The decision carries into later scans."""

from __future__ import annotations

from pydantic import Field

from mcp import links
from mcp.capabilities import Capability
from mcp.context import ToolContext
from mcp.dimensions import dimension
from mcp.errors import ToolError
from mcp.result import ToolResult
from mcp.tools._scope import resolve
from mcp.tools.base import Tool, ToolGroup, ToolInput
from shared.definitions.surface import SurfaceDimension
from shared.definitions.vulnerabilities import VulnState

STATES = tuple(s.value for s in VulnState)


class Input(ToolInput):
    target: str = Field(description="The target the finding was reported on.")
    fingerprint: str = Field(
        description="The finding's fingerprint, as returned by query_assets."
    )
    state: str = Field(description=f"The review decision. One of: {', '.join(STATES)}.")
    note: str | None = Field(
        default=None, max_length=2000, description="Why. Stored with the decision."
    )


class RecordTriage(Tool):
    name = "record_triage"
    title = "Record triage"
    capability = Capability.WRITE.value
    group = ToolGroup.ACT.value
    description = (
        "Record a review decision against a finding: confirmed, false positive, or "
        "accepted risk. The decision is keyed to the finding's fingerprint, so it "
        "carries into every later scan of that target and a suppressed finding stays "
        "suppressed. Always include a note saying why."
    )
    Input = Input
    examples = (
        "record_triage target=example.com fingerprint=<hash> state=false_positive "
        "note='Static asset, not the admin panel.'",
    )

    async def run(self, ctx: ToolContext, args: Input) -> ToolResult:
        from app.services.vulnerability import VulnerabilityService  # noqa: PLC0415
        from shared.models.vulnerability import TriageUpdate  # noqa: PLC0415

        if args.state not in STATES:
            msg = f"Unknown state {args.state!r}. Use one of: {', '.join(STATES)}."
            raise ToolError(msg)
        if ctx.token.issued_by is None:
            msg = "This token has no issuing operator, so a decision cannot be attributed."
            raise ToolError(msg)

        dim = dimension(SurfaceDimension.VULNERABILITIES.value)
        scope = await resolve(ctx, args.target)
        scan_id = scope.require(dim)

        result = await VulnerabilityService(ctx.session).triage(
            scan_id,
            args.fingerprint.strip(),
            TriageUpdate(state=args.state, note=args.note),
            ctx.token.issued_by,
        )
        if result is None:
            msg = (
                f"No finding with fingerprint {args.fingerprint!r} on "
                f"{scope.target.target_value}. Take the value from query_assets."
            )
            raise ToolError(msg)

        return ToolResult(
            summary=(
                f"Marked {result.updated} observation(s) as {result.state} "
                f"on {scope.target.target_value}"
            ),
            data={
                "fingerprint": result.fingerprint,
                "state": result.state,
                "note": result.note,
                "observations_updated": result.updated,
            },
            pivot=links.scan_tab(ctx.ui_base_url, scan_id, dim.tab),
            caveats=[
                "This decision applies to every later scan of this target.",
                f"Recorded by agent token '{ctx.token.name}' via MCP.",
            ],
        )
