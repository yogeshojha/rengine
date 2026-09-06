"""A dry run. Resolves exactly what would happen without touching the target."""

from __future__ import annotations

import uuid

from pydantic import Field

from mcp.capabilities import Capability
from mcp.context import ToolContext
from mcp.errors import ToolError
from mcp.result import ToolResult
from mcp.tools._scope import project_for
from mcp.tools.base import Tool, ToolGroup, ToolInput
from shared.models.scan_preview import PreviewToolStatus


class Input(ToolInput):
    target: str = Field(
        description="A target value. It does not have to exist in reNgine yet."
    )
    engine_id: str | None = Field(
        default=None,
        description="A saved scan engine to plan with. Omit for an ad hoc plan.",
    )
    stages: list[str] = Field(
        default_factory=list,
        max_length=20,
        description=(
            "Capability stages to enable for an ad hoc plan, for example "
            "subdomain_discovery, port_scan, http_probe, vulnerability_scan."
        ),
    )
    intensity: str | None = Field(
        default=None, description="passive, normal or aggressive."
    )


class PlanScan(Tool):
    name = "plan_scan"
    title = "Plan a scan"
    capability = Capability.PLAN.value
    group = ToolGroup.ACT.value
    description = (
        "Resolve what a scan would do — which stages run in which order, which are "
        "skipped and why, the footprint and the estimated duration — without starting "
        "anything and without contacting the target. "
        "Use it to answer 'what would this cost' and to check a plan before launching."
    )
    Input = Input
    examples = (
        "plan_scan target=example.com stages=['subdomain_discovery','http_probe']",
    )

    async def run(self, ctx: ToolContext, args: Input) -> ToolResult:
        from app.services.scan import ScanService  # noqa: PLC0415
        from shared.models.scan import ScanCreate  # noqa: PLC0415

        project_id = await project_for(ctx, None)
        payload = _scan_create(args, ScanCreate)

        try:
            preview = await ScanService(ctx.session).preview(payload, project_id)
        except Exception as exc:
            msg = f"That plan could not be resolved: {exc}"
            raise ToolError(msg) from exc

        phases = [
            {
                "phase": phase.label,
                "stages": [
                    {
                        "stage": tool.capability,
                        "label": tool.label,
                        "status": str(tool.status),
                        "reason": tool.reason,
                    }
                    for tool in phase.tools
                ],
            }
            for phase in preview.phases
        ]
        running = sum(
            1
            for phase in phases
            for stage in phase["stages"]
            if stage["status"] == PreviewToolStatus.WILL_RUN.value
        )

        return ToolResult(
            summary=(
                f"{running} stage(s) would run against {preview.target_value} "
                f"using {preview.engine_name}"
            ),
            data={
                "target": preview.target_value,
                "target_type": preview.target_type,
                "engine": preview.engine_name,
                "context": preview.context_name,
                "summary": preview.summary.model_dump(mode="json")
                if preview.summary
                else None,
                "phases": phases,
                "warnings": preview.warnings,
            },
            caveats=["Nothing ran. This is a resolution of the plan only."],
        )


def _scan_create(args: Input, model):
    overrides = {stage: {"enabled": True} for stage in args.stages}
    payload: dict = {"target_value": args.target.strip(), "overrides": overrides}
    if args.engine_id:
        try:
            payload["engine_id"] = uuid.UUID(args.engine_id)
        except ValueError as exc:
            msg = "engine_id must be a UUID."
            raise ToolError(msg) from exc
    if args.intensity:
        payload["intensity"] = args.intensity
    try:
        return model.model_validate(payload)
    except Exception as exc:
        msg = f"That plan is not valid: {exc}"
        raise ToolError(msg) from exc
