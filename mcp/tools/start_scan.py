"""Launch. The one read-write tool that reaches a machine the operator does not own."""

from __future__ import annotations

import uuid

from pydantic import Field

from mcp import links
from mcp.capabilities import Capability
from mcp.context import ToolContext
from mcp.errors import ToolError
from mcp.result import ToolResult
from mcp.tools._scope import project_for
from mcp.tools.base import Tool, ToolGroup, ToolInput


class Input(ToolInput):
    target: str = Field(
        description="The target to scan. Created in reNgine if it does not exist yet."
    )
    engine_id: str | None = Field(
        default=None, description="A saved scan engine. Omit for an ad hoc plan."
    )
    stages: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="Capability stages to enable when no engine is named.",
    )
    intensity: str | None = Field(
        default=None, description="passive, normal or aggressive."
    )
    context_id: str | None = Field(
        default=None, description="A saved scan context for auth, scope and rate."
    )


class StartScan(Tool):
    name = "start_scan"
    title = "Start a scan"
    capability = Capability.LAUNCH.value
    group = ToolGroup.ACT.value
    description = (
        "Start a scan against a target in this token's project. This sends traffic to "
        "the target, so run plan_scan first and tell the user what will happen. "
        "Returns immediately with a scan id and a link; scanning continues in the "
        "background. Poll resolve_target for progress rather than waiting."
    )
    Input = Input
    examples = ("start_scan target=example.com stages=['subdomain_discovery']",)

    async def run(self, ctx: ToolContext, args: Input) -> ToolResult:
        from app.services.scan import ScanService  # noqa: PLC0415
        from shared.models.scan import ScanCreate  # noqa: PLC0415

        if ctx.token.issued_by is None:
            msg = "This token has no issuing operator, so a scan cannot be attributed."
            raise ToolError(msg)

        project_id = await project_for(ctx, None)
        payload: dict = {
            "target_value": args.target.strip(),
            "overrides": {stage: {"enabled": True} for stage in args.stages},
        }
        for key, value in (
            ("engine_id", args.engine_id),
            ("context_id", args.context_id),
        ):
            if value:
                payload[key] = _uuid(value, key)
        if args.intensity:
            payload["intensity"] = args.intensity

        try:
            data = ScanCreate.model_validate(payload)
            scan = await ScanService(ctx.session).create(
                data, project_id, ctx.token.issued_by
            )
        except Exception as exc:
            msg = f"The scan could not be started: {exc}"
            raise ToolError(msg) from exc

        return ToolResult(
            summary=(
                f"Scan started on {scan.target_value or args.target} "
                f"with {scan.engine_name}"
            ),
            data={
                "scan_id": str(scan.id),
                "status": scan.status,
                "engine": scan.engine_name,
                "target": scan.target_value,
                "started_at": scan.started_at,
            },
            pivot=links.scan(ctx.ui_base_url, scan.id),
            caveats=[
                "Traffic is now being sent to this target.",
                f"Started by agent token '{ctx.token.name}' via MCP.",
            ],
        )


def _uuid(value: str, field: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        msg = f"{field} must be a UUID."
        raise ToolError(msg) from exc
