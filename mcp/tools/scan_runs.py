"""A run an agent started, and the brake for it. Nothing else took a scan id."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field
from sqlmodel import select

from mcp import links
from mcp.capabilities import Capability
from mcp.context import ToolContext
from mcp.dimensions import dimension
from mcp.errors import ToolError
from mcp.result import ToolResult
from mcp.tools._scope import find_target
from mcp.tools.base import Tool, ToolGroup, ToolInput
from shared.definitions.surface import SurfaceDimension
from shared.enums.scan import SCAN_LIVE_STATUSES, ScanActivityStatus
from shared.models.scan import Scan
from shared.models.target import Target
from shared.utils.datetime import utc_now

MAX_RUNS = 20

# the run's own rollup column per dimension; final figures come from resolve_target
ROLLUP: dict[str, str] = {
    SurfaceDimension.WEB_ASSETS.value: "subdomains_found",
    SurfaceDimension.IPS.value: "ips_found",
    SurfaceDimension.SERVICES.value: "open_ports_found",
    SurfaceDimension.ENDPOINTS.value: "endpoints_found",
    SurfaceDimension.VULNERABILITIES.value: "vulnerabilities_found",
}

DONE = (ScanActivityStatus.SUCCESS.value, ScanActivityStatus.PARTIAL.value)


class StatusInput(ToolInput):
    scan: str | None = Field(
        default=None,
        description="A scan id, as returned by start_scan or focused_rescan.",
    )
    target: str | None = Field(
        default=None, description="A target, to report its most recent run."
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=MAX_RUNS,
        description="How many runs to list when neither scan nor target is named.",
    )


class ScanStatus(Tool):
    name = "scan_status"
    title = "Scan status"
    group = ToolGroup.ORIENT.value
    description = (
        "Where a scan has got to: its status, which stages have finished, which are "
        "running, which failed, and what it has found so far. Call it with the id "
        "start_scan returned to follow that run, with a target for its most recent "
        "run, or with neither to see everything currently running. Poll this rather "
        "than waiting — a scan takes minutes to hours."
    )
    Input = StatusInput
    examples = (
        "scan_status",
        "scan_status target=example.com",
        "scan_status scan=<id>",
    )

    async def run(self, ctx: ToolContext, args: StatusInput) -> ToolResult:
        if not args.scan and not args.target:
            return await _running(ctx, args.limit)

        row = await _one_run(ctx, args.scan, args.target)
        stages = await _stages(ctx, row)
        live = row.status in SCAN_LIVE_STATUSES
        return ToolResult(
            summary=_status_line(row, stages, live),
            data=_describe(row, stages),
            pivot=links.scan(ctx.ui_base_url, row.id),
            caveats=_status_caveats(row, live),
        )


class CancelInput(ToolInput):
    scan: str | None = Field(default=None, description="The scan id to stop.")
    target: str | None = Field(
        default=None, description="A target, to stop whichever run of it is live."
    )


class CancelScan(Tool):
    name = "cancel_scan"
    title = "Cancel a scan"
    capability = Capability.LAUNCH.value
    group = ToolGroup.ACT.value
    description = (
        "Stop a running scan. Traffic to the target stops, the stages still in flight "
        "are aborted, and everything the run had already found is kept and stays "
        "queryable. Use it as soon as a scan is pointed somewhere it should not be — "
        "it takes effect immediately and needs no confirmation."
    )
    Input = CancelInput
    examples = ("cancel_scan target=example.com", "cancel_scan scan=<id>")

    async def run(self, ctx: ToolContext, args: CancelInput) -> ToolResult:
        from app.services.scan import ScanService  # noqa: PLC0415

        if not args.scan and not args.target:
            msg = "Name the scan to stop, by scan id or by target. scan_status lists what is running."
            raise ToolError(msg)

        row = await _one_run(ctx, args.scan, args.target, live_only=bool(args.target))
        if row.status not in SCAN_LIVE_STATUSES:
            msg = (
                f"That scan is already {row.status}, so there is nothing to stop. "
                f"Its results stay queryable."
            )
            raise ToolError(msg)

        result = await ScanService(ctx.session).cancel(row.id, row.project_id)
        target = await ctx.session.get(Target, row.target_id)
        return ToolResult(
            summary=f"Stopped the scan of {target.target_value if target else row.target_id}",
            data={
                "scan_id": str(result.id),
                "status": result.status,
                "engine": result.engine_name,
                "kept": _found(result),
            },
            pivot=links.scan(ctx.ui_base_url, result.id),
            caveats=[
                "What the run found before stopping is kept and stays queryable.",
                "The dimensions its remaining stages would have covered were never scanned — that is not the same as finding nothing.",
                f"Stopped by agent token '{ctx.token.name}' via MCP.",
            ],
        )


async def _one_run(
    ctx: ToolContext, scan: str | None, target: str | None, live_only: bool = False
) -> Scan:
    if scan:
        row = await ctx.session.get(Scan, _uuid(scan, "scan"))
        if row is None:
            msg = (
                f"No scan with id {scan!r}. Take the id from start_scan or scan_status."
            )
            raise ToolError(msg)
        ctx.check_project(row.project_id)
        return row

    found = await find_target(ctx, target or "")
    statement = select(Scan).where(Scan.target_id == found.id)
    if live_only:
        statement = statement.where(Scan.status.in_(SCAN_LIVE_STATUSES))
    row = (
        await ctx.session.execute(statement.order_by(Scan.created_at.desc()).limit(1))
    ).scalar_one_or_none()
    if row is None:
        msg = (
            f"No {'running ' if live_only else ''}scan of {found.target_value}. "
            f"{'Nothing to stop.' if live_only else 'Start one with start_scan.'}"
        )
        raise ToolError(msg)
    return row


async def _running(ctx: ToolContext, limit: int) -> ToolResult:
    statement = select(Scan).where(Scan.status.in_(SCAN_LIVE_STATUSES))
    scoped = ctx.scoped_projects()
    if scoped is not None:
        statement = statement.where(Scan.project_id.in_(scoped))
    rows = list(
        (
            await ctx.session.execute(
                statement.order_by(Scan.created_at.desc()).limit(limit)
            )
        )
        .scalars()
        .all()
    )
    live = bool(rows)
    if not rows:
        recent = select(Scan)
        if scoped is not None:
            recent = recent.where(Scan.project_id.in_(scoped))
        rows = list(
            (
                await ctx.session.execute(
                    recent.order_by(Scan.created_at.desc()).limit(limit)
                )
            )
            .scalars()
            .all()
        )

    targets = {t.id: t.target_value for t in await _targets(ctx, rows)}
    return ToolResult(
        summary=(
            f"{len(rows)} scan(s) running"
            if live
            else f"Nothing is running. The {len(rows)} most recent run(s):"
        ),
        data=[
            {
                "scan_id": str(row.id),
                "target": targets.get(row.target_id),
                "engine": row.engine_name,
                "status": row.status,
                "started_at": row.started_at,
                "elapsed_seconds": _elapsed(row),
            }
            for row in rows
        ],
        pivot=f"{ctx.ui_base_url.rstrip('/')}/scans",
        caveats=[]
        if live
        else ["Start one with start_scan, or query what earlier runs found."],
    )


async def _targets(ctx: ToolContext, rows: list[Scan]) -> list[Target]:
    ids = {row.target_id for row in rows}
    if not ids:
        return []
    return list(
        (await ctx.session.execute(select(Target).where(Target.id.in_(ids))))
        .scalars()
        .all()
    )


async def _stages(ctx: ToolContext, row: Scan) -> dict[str, list[str]]:
    from app.services.scan import ScanService  # noqa: PLC0415

    activities = await ScanService(ctx.session).list_activities(row.id, row.project_id)
    out: dict[str, list[str]] = {"done": [], "running": [], "failed": [], "skipped": []}
    for activity in activities:
        if activity.status in DONE:
            out["done"].append(activity.title)
        elif activity.status == ScanActivityStatus.RUNNING.value:
            out["running"].append(activity.title)
        elif activity.status in (
            ScanActivityStatus.FAILED.value,
            ScanActivityStatus.ABORTED.value,
        ):
            out["failed"].append(activity.title)
        elif activity.status == ScanActivityStatus.SKIPPED.value:
            out["skipped"].append(activity.title)
    # a stage can hold several activity rows; the agent wants the stage, once
    return {key: list(dict.fromkeys(titles)) for key, titles in out.items()}


def _describe(row: Scan, stages: dict[str, list[str]]) -> dict:
    return {
        "scan_id": str(row.id),
        "status": row.status,
        "engine": row.engine_name,
        "started_at": row.started_at,
        "completed_at": row.completed_at,
        "elapsed_seconds": _elapsed(row),
        "stages": {key: value for key, value in stages.items() if value},
        "found_so_far": _found(row),
        "error": row.error,
    }


def _found(row) -> dict[str, int]:
    return {
        dimension(key).label: int(getattr(row, column, 0) or 0)
        for key, column in ROLLUP.items()
    }


def _status_line(row: Scan, stages: dict[str, list[str]], live: bool) -> str:
    done = len(stages["done"])
    total = (
        done + len(stages["running"]) + len(stages["failed"]) + len(stages["skipped"])
    )
    if live:
        now = ", ".join(stages["running"][:3]) or "starting"
        return f"{row.status} — {done} of {total} stages done, now: {now}"
    failed = f", {len(stages['failed'])} stage(s) failed" if stages["failed"] else ""
    return f"{row.status} — {done} stage(s) completed{failed}"


def _status_caveats(row: Scan, live: bool) -> list[str]:
    notes = []
    if live:
        notes.append(
            "Counts are partial and rise as stages finish. Poll again rather than waiting."
        )
    else:
        notes.append(
            "These are the run's own rollup. For a target's current surface use resolve_target."
        )
    if row.error:
        notes.append(f"The run recorded an error: {row.error}")
    return notes


def _elapsed(row: Scan) -> float | None:
    start: datetime | None = row.started_at
    if start is None:
        return None
    end = row.completed_at or utc_now()
    return round((end - start).total_seconds(), 1)


def _uuid(value: str, field: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        msg = f"{field} must be a uuid, not {value!r}."
        raise ToolError(msg) from exc
