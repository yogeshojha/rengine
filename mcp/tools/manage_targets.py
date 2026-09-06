"""Target lifecycle: what an agent needs before there is anything to scan or query."""

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
        description=f"The values to add, each {KINDS}. Already-present values are reused, not duplicated.",
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
        "Add one or more targets to a project so they can be scanned and queried. "
        "This only records the target and queues WHOIS, DNS and routing enrichment — "
        "it sends no traffic and runs no scan; use start_scan for that. A value "
        "already in the project is reused rather than duplicated, so this is safe to "
        "repeat."
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
            msg = f"Not a target reNgine can add: {', '.join(rejected)}. Give {KINDS}."
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
        description="Replaces the target's tags outright. Pass [] to clear them.",
    )
    organizations: list[str] | None = Field(
        default=None,
        max_length=MAX_LABELS,
        description="Replaces the target's organizations outright.",
    )


class UpdateTarget(Tool):
    name = "update_target"
    title = "Update a target"
    capability = Capability.WRITE.value
    group = ToolGroup.ACT.value
    description = (
        "Change how a target is labelled: its display name, its tags, its "
        "organizations. Tags and organizations are replaced by what you pass, not "
        "merged, so read the target first if you mean to add one. The target value "
        "itself cannot be changed — add a new target and delete the old one."
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
        description="Must be true. Call once without it to see what would be destroyed.",
    )


class DeleteTarget(Tool):
    name = "delete_target"
    title = "Delete a target"
    capability = Capability.WRITE.value
    group = ToolGroup.ACT.value
    destructive = True
    description = (
        "Delete a target and everything recorded against it: every scan, every web "
        "asset, service, endpoint and finding, and every triage decision. This cannot "
        "be undone and there is no export first. Call it without `confirm` to be told "
        "what would be lost, show that to the user, and only then call again with "
        "confirm=true."
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
                f"Deleting is permanent. Show this to the user, and call "
                f"delete_target target={value!r} confirm=true only if they agree."
            )
            raise ToolError(msg)

        await _guard(
            TargetService(ctx.session).delete_target(str(scope.target.id), operator)
        )
        return ToolResult(
            summary=f"Deleted {value} and everything recorded against it",
            data={"value": value, "scans_deleted": scans, "results_deleted": holdings},
            pivot=f"{ctx.ui_base_url.rstrip('/')}/targets",
            caveats=[
                "This cannot be undone.",
                f"Deleted by agent token '{ctx.token.name}' via MCP.",
            ],
        )


def _operator(ctx: ToolContext) -> uuid.UUID:
    if ctx.token.issued_by is None:
        msg = "This token has no issuing operator, so the change cannot be attributed."
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
        tail.append(f"{reused} already present")
    if rejected:
        tail.append(f"{len(rejected)} rejected")
    return f"{head} ({', '.join(tail)})" if tail else head


def _added_caveats(created: list[Target], rejected: list[str]) -> list[str]:
    notes = []
    if created:
        notes.append(
            "WHOIS, DNS and routing enrichment is queued and takes a few seconds."
        )
        notes.append(
            "Nothing has been scanned yet — every dimension reads as never scanned until start_scan runs."
        )
    if rejected:
        notes.append(f"Not a value reNgine can target: {', '.join(rejected)}.")
    return notes


def _holdings_line(value: str, scans: int, holdings: dict[str, int | None]) -> str:
    if not scans:
        return f"{value} has no scans recorded."
    kept = ", ".join(f"{count} {label.lower()}" for label, count in holdings.items())
    runs = f"{scans} scan{'s' if scans != 1 else ''}"
    return f"Deleting {value} would destroy {runs}" + (
        f" holding {kept}." if kept else "."
    )
