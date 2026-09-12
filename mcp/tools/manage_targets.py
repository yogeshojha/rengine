"""Target lifecycle: add, update, delete."""

from __future__ import annotations

import uuid

from pydantic import Field
from sqlmodel import select

from mcp import links
from mcp.capabilities import Capability
from mcp.context import ToolContext
from mcp.errors import ToolError
from mcp.result import ToolResult
from mcp.tools._scope import project_for, resolve
from mcp.tools.base import Tool, ToolGroup, ToolInput
from shared.models.project import Project
from shared.models.target import Target

MAX_VALUES = 50
MAX_LABELS = 20
KINDS = "a domain, IP address, CIDR range, URL or ASN"


class AddInput(ToolInput):
    targets: list[str] = Field(
        min_length=1,
        max_length=MAX_VALUES,
        description=f"The values to add, each {KINDS}. Existing values are reused.",
    )
    project_id: str | None = Field(
        default=None,
        description="Which project to add them to. Omit when the token is scoped to one.",
    )
    tags: list[str] = Field(
        default_factory=list,
        max_length=MAX_LABELS,
        description="Tags applied to the targets this call creates. Existing targets keep theirs.",
    )
    organizations: list[str] = Field(
        default_factory=list,
        max_length=MAX_LABELS,
        description="Organizations applied to the targets this call creates.",
    )


class AddTarget(Tool):
    name = "add_target"
    title = "Add targets"
    capability = Capability.WRITE.value
    group = ToolGroup.ACT.value
    description = (
        "Add targets to a project. Records each target and queues WHOIS, DNS and "
        "routing enrichment. Runs no scan. An existing value is reused."
    )
    Input = AddInput
    examples = (
        "add_target targets=['example.com']",
        "add_target targets=['example.com','1.1.1.1'] tags=['client-a']",
    )

    async def run(self, ctx: ToolContext, args: AddInput) -> ToolResult:
        from app.services.target import TargetService  # noqa: PLC0415
        from shared.models.target import TargetUpdate  # noqa: PLC0415

        operator = _operator(ctx)
        project_id = await project_for(ctx, _uuid(args.project_id, "project_id"))
        service = TargetService(ctx.session)

        wanted: list[str] = []
        rejected: list[str] = []
        seen: set[str] = set()
        for raw in args.targets:
            value = raw.strip()
            if not value or value.lower() in seen:
                continue
            seen.add(value.lower())
            if await service.validate_target_value(value) is None:
                rejected.append(value)
            else:
                wanted.append(value)

        if not wanted:
            msg = f"Not a valid target: {', '.join(rejected)}. Give {KINDS}."
            raise ToolError(msg)

        present = set(
            (
                await ctx.session.execute(
                    select(Target.target_value).where(
                        Target.project_id == project_id,
                        Target.target_value.in_(wanted),
                    )
                )
            )
            .scalars()
            .all()
        )

        rows = await _guard(service.ensure_targets(wanted, project_id, operator))
        created = [row for row in rows if row.target_value not in present]

        if created and (args.tags or args.organizations):
            patch = TargetUpdate(
                tag_names=args.tags or None,
                organization_names=args.organizations or None,
            )
            for row in created:
                await _guard(service.update_target(str(row.id), patch, operator))

        project = await ctx.session.get(Project, project_id)
        return ToolResult(
            summary=_added_line(created, len(rows) - len(created), rejected, project),
            data={
                "project": project.name if project else str(project_id),
                "created": [_describe(ctx, row) for row in created],
                "already_present": sorted(present),
                "rejected": rejected,
            },
            pivot=(
                links.target(ctx.ui_base_url, created[0].id)
                if len(created) == 1 and not present
                else f"{ctx.ui_base_url.rstrip('/')}/targets"
            ),
            caveats=_added_caveats(created, rejected),
        )


class UpdateInput(ToolInput):
    target: str = Field(description="The target to change, by value or id.")
    display_name: str | None = Field(
        default=None, max_length=200, description="The name shown in the UI."
    )
    tags: list[str] | None = Field(
        default=None,
        max_length=MAX_LABELS,
        description="Replaces the target's tags. Pass [] to clear them.",
    )
    organizations: list[str] | None = Field(
        default=None,
        max_length=MAX_LABELS,
        description="Replaces the target's organizations.",
    )


class UpdateTarget(Tool):
    name = "update_target"
    title = "Update a target"
    capability = Capability.WRITE.value
    group = ToolGroup.ACT.value
    description = (
        "Change a target's display name, tags or organizations. Tags and "
        "organizations are replaced, not merged. The target value cannot be changed."
    )
    Input = UpdateInput
    examples = ("update_target target=example.com tags=['client-a','production']",)

    async def run(self, ctx: ToolContext, args: UpdateInput) -> ToolResult:
        from app.services.target import TargetService  # noqa: PLC0415
        from shared.models.target import TargetUpdate  # noqa: PLC0415

        operator = _operator(ctx)
        if (
            args.display_name is None
            and args.tags is None
            and args.organizations is None
        ):
            msg = "Nothing to change. Pass display_name, tags or organizations."
            raise ToolError(msg)

        scope = await resolve(ctx, args.target)
        result = await _guard(
            TargetService(ctx.session).update_target(
                str(scope.target.id),
                TargetUpdate(
                    display_name=args.display_name,
                    tag_names=args.tags,
                    organization_names=args.organizations,
                ),
                operator,
            )
        )
        return ToolResult(
            summary=f"Updated {result.target_value}",
            data={
                "value": result.target_value,
                "display_name": result.display_name,
                "tags": [t.name for t in result.tags],
                "organizations": [o.name for o in result.organizations],
            },
            pivot=links.target(ctx.ui_base_url, result.id),
        )


class DeleteInput(ToolInput):
    target: str = Field(description="The target to delete, by value or id.")
    confirm: bool = Field(
        default=False,
        description="Must be true. A call without it returns what would be deleted.",
    )


class DeleteTarget(Tool):
    name = "delete_target"
    title = "Delete a target"
    capability = Capability.WRITE.value
    group = ToolGroup.ACT.value
    destructive = True
    description = (
        "Delete a target and everything recorded against it: scans, web assets, "
        "services, endpoints, findings and triage decisions. A call without "
        "`confirm` returns what would be deleted. Call with confirm=true after the "
        "user agrees."
    )
    Input = DeleteInput
    examples = ("delete_target target=old.example.com confirm=true",)

    async def run(self, ctx: ToolContext, args: DeleteInput) -> ToolResult:
        from app.services.target import TargetService  # noqa: PLC0415

        operator = _operator(ctx)
        scope = await resolve(ctx, args.target)
        value = scope.target.target_value
        holdings = {
            metric.label: metric.value
            for metric in scope.summary.surface
            if metric.covered and metric.value
        }
        scans = scope.summary.scans_total

        if not args.confirm:
            msg = (
                f"Not deleted. {_holdings_line(value, scans, holdings)} "
                f"Call delete_target target={value!r} confirm=true after the user "
                f"agrees."
            )
            raise ToolError(msg)

        await _guard(
            TargetService(ctx.session).delete_target(str(scope.target.id), operator)
        )
        return ToolResult(
            summary=f"Deleted {value} and everything recorded against it",
            data={"value": value, "scans_deleted": scans, "results_deleted": holdings},
            pivot=f"{ctx.ui_base_url.rstrip('/')}/targets",
            caveats=[f"Deleted by agent token '{ctx.token.name}' via MCP."],
        )


def _operator(ctx: ToolContext) -> uuid.UUID:
    if ctx.token.issued_by is None:
        msg = "This token has no issuing operator to attribute the change to."
        raise ToolError(msg)
    return ctx.token.issued_by


def _uuid(value: str | None, field: str) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        msg = f"{field} must be a uuid, not {value!r}."
        raise ToolError(msg) from exc


async def _guard(awaitable):
    """Turn a service HTTPException into a message the model can act on."""
    from fastapi import HTTPException  # noqa: PLC0415

    try:
        return await awaitable
    except HTTPException as exc:
        raise ToolError(str(exc.detail)) from exc


def _describe(ctx: ToolContext, row: Target) -> dict:
    return {
        "id": str(row.id),
        "value": row.target_value,
        "type": getattr(row.target_type, "value", str(row.target_type)),
        "link": links.target(ctx.ui_base_url, row.id),
    }


def _added_line(
    created: list[Target], reused: int, rejected: list[str], project: Project | None
) -> str:
    where = f" to {project.name}" if project else ""
    if not created:
        head = f"Nothing added{where}"
    elif len(created) == 1:
        head = f"Added {created[0].target_value}{where}"
    else:
        head = f"Added {len(created)} targets{where}"
    tail = []
    if reused:
        tail.append(f"{reused} existing")
    if rejected:
        tail.append(f"{len(rejected)} rejected")
    return f"{head} ({', '.join(tail)})" if tail else head


def _added_caveats(created: list[Target], rejected: list[str]) -> list[str]:
    notes = []
    if created:
        notes.append("WHOIS, DNS and routing enrichment is queued.")
        notes.append("No dimension is scanned until start_scan runs.")
    if rejected:
        notes.append(f"Not a valid target: {', '.join(rejected)}.")
    return notes


def _holdings_line(value: str, scans: int, holdings: dict[str, int | None]) -> str:
    if not scans:
        return f"{value} has no scans recorded."
    kept = ", ".join(f"{count} {label.lower()}" for label, count in holdings.items())
    runs = f"{scans} scan{'s' if scans != 1 else ''}"
    return f"Deleting {value} removes {runs}" + (f" holding {kept}." if kept else ".")
