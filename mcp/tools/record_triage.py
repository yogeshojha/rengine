"""Record a triage decision."""

from __future__ import annotations

from pydantic import Field

from mcp import links
from mcp.capabilities import Capability
from mcp.context import ToolContext
from mcp.dimensions import dimension
from mcp.errors import ToolError
from mcp.result import ToolResult
from mcp.tools._scope import operator, resolve
from mcp.tools.base import Tool, ToolGroup, ToolInput
from shared.definitions.notes import MAX_NOTE_BODY
from shared.definitions.surface import SurfaceDimension
from shared.definitions.vulnerabilities import VULN_STATES
from shared.utils.text import counted


class Input(ToolInput):
    target: str = Field(description="The target the finding was reported on.")
    fingerprint: str = Field(
        description="The finding's fingerprint, as returned by query_assets."
    )
    state: str = Field(
        description=f"The review decision. One of: {', '.join(VULN_STATES)}."
    )
    reason: str | None = Field(
        default=None,
        max_length=MAX_NOTE_BODY,
        description="The reason for the decision. Saved as a note on the finding.",
    )


class RecordTriage(Tool):
    name = "record_triage"
    title = "Record triage"
    capability = Capability.WRITE.value
    group = ToolGroup.ACT.value
    description = (
        "Record a review decision against a finding: confirmed, false positive or "
        "accepted risk. The decision is keyed to the fingerprint and applies to "
        "every later scan of the target. Include a reason."
    )
    Input = Input
    examples = (
        "record_triage target=example.com fingerprint=<hash> state=false_positive "
        "reason='Static asset, not the admin panel.'",
    )

    async def run(self, ctx: ToolContext, args: Input) -> ToolResult:
        from app.services.vulnerability import VulnerabilityService  # noqa: PLC0415
        from shared.models.vulnerability import (  # noqa: PLC0415
            TriageUpdate,
            check_reason,
        )

        if args.state not in VULN_STATES:
            msg = f"Unknown state {args.state!r}. Use one of: {', '.join(VULN_STATES)}."
            raise ToolError(msg)
        try:
            reason = check_reason(args.state, args.reason)
        except ValueError as exc:
            raise ToolError(str(exc)) from None
        issued_by = operator(ctx)

        dim = dimension(SurfaceDimension.VULNERABILITIES.value)
        scope = await resolve(ctx, args.target)
        scan_id = scope.require(dim)

        result = await VulnerabilityService(ctx.session).triage(
            scan_id,
            args.fingerprint.strip(),
            TriageUpdate(state=args.state, reason=reason),
            issued_by,
        )
        if result is None:
            msg = (
                f"No finding with fingerprint {args.fingerprint!r} on "
                f"{scope.target.target_value}. Take the value from query_assets."
            )
            raise ToolError(msg)

        return ToolResult(
            summary=(
                f"Marked {counted(result.updated, 'observation')} as {result.state} "
                f"on {scope.target.target_value}"
            ),
            data={
                "fingerprint": result.fingerprint,
                "state": result.state,
                "reason": result.reason,
                "observations_updated": result.updated,
            },
            pivot=links.scan_tab(ctx.ui_base_url, scan_id, dim.tab),
            caveats=[
                "This decision applies to every later scan of this target.",
                f"Recorded by agent token '{ctx.token.name}' via MCP.",
            ],
        )
