"""Launch."""

from __future__ import annotations

import uuid

from pydantic import Field, ValidationError
from sqlmodel import select

from mcp import links
from mcp.capabilities import Capability
from mcp.context import ToolContext
from mcp.errors import CapabilityError, ToolError
from mcp.phrasing import short_id
from mcp.result import ToolResult
from mcp.tools._scope import operator, parse_id, project_for
from mcp.tools.base import Tool, ToolGroup, ToolInput
from shared.enums.scan import INTENSITIES, Intensity
from shared.models.target import Target
from shared.utils.validation import normalize_target_value
from toolbox.base import fact, facts, hero


class Input(ToolInput):
    target: str = Field(
        description=(
            "The target to scan. A value not yet in the project is added when the "
            "token holds the write capability."
        )
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
        default=None, description=f"One of: {', '.join(INTENSITIES)}."
    )
    context_id: str | None = Field(
        default=None, description="A saved scan context for auth, scope and rate."
    )
    project_id: str | None = Field(
        default=None,
        description="Project to act in. Omit when the token is scoped to one.",
    )


class StartScan(Tool):
    name = "start_scan"
    command = "scan"
    value_field = "target"
    title = "Start a scan"
    capability = Capability.LAUNCH.value
    group = ToolGroup.ACT.value
    description = (
        "Start a scan against a target in this token's project. Sends traffic to the "
        "target. Returns a scan id and a link. The scan runs in the background. "
        "Poll scan_status for progress."
    )
    Input = Input
    examples = ("start_scan target=example.com stages=['subdomain_discovery']",)

    async def run(self, ctx: ToolContext, args: Input) -> ToolResult:
        from fastapi import HTTPException  # noqa: PLC0415

        from app.services.scan import ScanService  # noqa: PLC0415
        from shared.models.scan import ScanCreate  # noqa: PLC0415

        issued_by = operator(ctx)
        project_id = await project_for(ctx, parse_id(args.project_id, "project_id"))
        payload: dict = {
            **await _target_of(ctx, args.target, project_id),
            "overrides": {stage: {"enabled": True} for stage in args.stages},
        }
        for key, value in (
            ("engine_id", args.engine_id),
            ("context_id", args.context_id),
        ):
            if value:
                payload[key] = parse_id(value, key)
        if args.intensity:
            payload["intensity"] = args.intensity

        try:
            data = ScanCreate.model_validate(payload)
            scan = await ScanService(ctx.session).create(data, project_id, issued_by)
        except HTTPException as exc:
            msg = f"Scan not started: {exc.detail}"
            raise ToolError(msg) from exc
        except ValidationError as exc:
            reason = str(exc.errors()[0].get("msg", "invalid input")).rstrip(".")
            msg = f"Scan not started: {reason}."
            raise ToolError(msg) from exc

        target = args.target.strip()
        return ToolResult(
            summary=f"Scan started on {target} with {scan.engine_name}",
            data={
                "scan_id": str(scan.id),
                "status": scan.status,
                "engine": scan.engine_name,
                "target": target,
                "target_id": str(scan.target_id),
                "started_at": scan.started_at,
            },
            pivot=links.scan(ctx.ui_base_url, scan.id),
            caveats=[
                _traffic_note(scan),
                "scan_status follows the run. cancel_scan stops it.",
                f"Started by agent token '{ctx.token.name}' via MCP.",
            ],
            blocks=[
                hero(f"Scan started on {target}", sub=scan.engine_name),
                facts(fact("Scan", short_id(scan.id), mono=True)),
            ],
        )


async def _target_of(ctx: ToolContext, value: str, project_id: uuid.UUID) -> dict:
    """The project's target for a value, or the value itself when write allows adding it."""
    normal = normalize_target_value(value)
    found = (
        await ctx.session.execute(
            select(Target.id).where(
                Target.project_id == project_id, Target.target_value == normal
            )
        )
    ).scalar_one_or_none()
    if found is not None:
        ctx.check_target(found)
        return {"target_id": found}
    if not ctx.token.allows(Capability.WRITE.value):
        msg = (
            f"{normal or value.strip()} is not a target in this project. "
            f"Adding a target needs the {Capability.WRITE.value} capability."
        )
        raise CapabilityError(msg)
    ctx.check_target(None)
    return {"target_value": value.strip()}


def _traffic_note(scan) -> str:
    passive = scan.execution_config.intensity == Intensity.PASSIVE.value
    return (
        "Passive intensity. No traffic reaches the target."
        if passive
        else "Traffic is being sent to the target."
    )
