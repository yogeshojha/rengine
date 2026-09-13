"""Scan status, pause, resume and cancellation."""

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
from shared.enums.scan import (
    SCAN_LIVE_STATUSES,
    SCAN_OPEN_STATUSES,
    ScanActivityStatus,
)
from shared.enums.scan import ScanStatus as RunStatus
from shared.models.scan import Scan
from shared.models.target import Target
from shared.utils.datetime import utc_now
from shared.utils.text import counted

MAX_RUNS = 20

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
        "Status of a scan: stages finished, running and failed, and counts found so "
        "far. Pass a scan id, a target for its most recent run, or neither for every "
        "running scan."
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
            caveats=_status_caveats(row, row.status in SCAN_OPEN_STATUSES),
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
        "Stop a running scan. Stages in flight are aborted. Results written so far "
        "are kept. Takes effect immediately."
    )
    Input = CancelInput
    examples = ("cancel_scan target=example.com", "cancel_scan scan=<id>")

    async def run(self, ctx: ToolContext, args: CancelInput) -> ToolResult:
        from app.services.scan import ScanService  # noqa: PLC0415

        if not args.scan and not args.target:
            msg = "Name the scan to stop, by scan id or by target. scan_status lists what is running."
            raise ToolError(msg)

        row = await _one_run(
            ctx,
            args.scan,
            args.target,
            statuses=SCAN_OPEN_STATUSES,
            state="unfinished",
            hint="Nothing to stop.",
        )
        if row.status not in SCAN_OPEN_STATUSES:
            msg = f"The scan is {row.status}. Nothing to stop."
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
                "Results written before the stop are kept.",
                "Dimensions the remaining stages would have covered are not scanned.",
                f"Stopped by agent token '{ctx.token.name}' via MCP.",
            ],
        )


class PauseInput(ToolInput):
    scan: str | None = Field(default=None, description="The scan id to pause.")
    target: str | None = Field(
        default=None, description="A target, to pause whichever run of it is live."
    )


class PauseScan(Tool):
    name = "pause_scan"
    title = "Pause a scan"
    capability = Capability.LAUNCH.value
    group = ToolGroup.ACT.value
    description = (
        "Pause a running scan. Stages in flight stop and run again from the start "
        "when the scan resumes. Results written so far are kept."
    )
    Input = PauseInput
    examples = ("pause_scan target=example.com", "pause_scan scan=<id>")

    async def run(self, ctx: ToolContext, args: PauseInput) -> ToolResult:
        from app.services.scan import ScanService  # noqa: PLC0415

        if not args.scan and not args.target:
            msg = "Name the scan to pause, by scan id or by target. scan_status lists what is running."
            raise ToolError(msg)

        row = await _one_run(
            ctx,
            args.scan,
            args.target,
            statuses=SCAN_LIVE_STATUSES,
            state="running",
            hint="Nothing to pause.",
        )
        if row.status not in SCAN_LIVE_STATUSES:
            msg = f"The scan is {row.status}. Nothing to pause."
            raise ToolError(msg)

        result = await ScanService(ctx.session).pause(row.id, row.project_id)
        target = await ctx.session.get(Target, row.target_id)
        return ToolResult(
            summary=f"Paused the scan of {target.target_value if target else row.target_id}",
            data={
                "scan_id": str(result.id),
                "status": result.status,
                "engine": result.engine_name,
                "kept": _found(result),
            },
            pivot=links.scan(ctx.ui_base_url, result.id),
            caveats=[
                "Stages that were running re-run from the start on resume.",
                "resume_scan continues the run at its first unfinished stage.",
                f"Paused by agent token '{ctx.token.name}' via MCP.",
            ],
        )


class ResumeInput(ToolInput):
    scan: str | None = Field(default=None, description="The scan id to resume.")
    target: str | None = Field(
        default=None, description="A target, to resume its paused run."
    )


class ResumeScan(Tool):
    name = "resume_scan"
    title = "Resume a scan"
    capability = Capability.LAUNCH.value
    group = ToolGroup.ACT.value
    description = (
        "Resume a paused scan. It restarts at its first unfinished stage. Stages "
        "that already succeeded are not run again."
    )
    Input = ResumeInput
    examples = ("resume_scan target=example.com", "resume_scan scan=<id>")

    async def run(self, ctx: ToolContext, args: ResumeInput) -> ToolResult:
        from app.services.scan import ScanService  # noqa: PLC0415

        if not args.scan and not args.target:
            msg = "Name the scan to resume, by scan id or by target."
            raise ToolError(msg)

        row = await _one_run(
            ctx,
            args.scan,
            args.target,
            statuses=(RunStatus.PAUSED.value,),
            state="paused",
            hint="Nothing to resume.",
        )
        if row.status != RunStatus.PAUSED.value:
            msg = f"The scan is {row.status}. Nothing to resume."
            raise ToolError(msg)

        result = await ScanService(ctx.session).resume(row.id, row.project_id)
        target = await ctx.session.get(Target, row.target_id)
        return ToolResult(
            summary=f"Resuming the scan of {target.target_value if target else row.target_id}",
            data={
                "scan_id": str(result.id),
                "status": result.status,
                "engine": result.engine_name,
            },
            pivot=links.scan(ctx.ui_base_url, result.id),
            caveats=[
                "The worker picks the run up. scan_status reports it running.",
                f"Resumed by agent token '{ctx.token.name}' via MCP.",
            ],
        )


async def _one_run(
    ctx: ToolContext,
    scan: str | None,
    target: str | None,
    statuses: tuple[str, ...] | None = None,
    state: str = "",
    hint: str = "Start one with start_scan.",
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
    if statuses is not None:
        statement = statement.where(Scan.status.in_(statuses))
    row = (
        await ctx.session.execute(statement.order_by(Scan.created_at.desc()).limit(1))
    ).scalar_one_or_none()
    if row is None:
        named = f"{state} " if state else ""
        msg = f"No {named}scan of {found.target_value}. {hint}"
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
            f"{counted(len(rows), 'scan')} running"
            if live
            else f"Nothing is running. The {counted(len(rows), 'most recent run')}:"
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
        caveats=[] if live else ["Start one with start_scan."],
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
        return f"{row.status}: {done} of {total} stages done, running {now}"
    failed = (
        f", {counted(len(stages['failed']), 'stage')} failed"
        if stages["failed"]
        else ""
    )
    return f"{row.status}: {counted(done, 'stage')} completed{failed}"


def _status_caveats(row: Scan, unfinished: bool) -> list[str]:
    notes = []
    if unfinished:
        notes.append("The run has not finished. Counts are partial.")
    else:
        notes.append(
            "Counts are the run's own rollup. resolve_target gives the target's "
            "current surface."
        )
    if row.error:
        notes.append(f"The run recorded an error: {row.error}")
    return notes


def _elapsed(row: Scan) -> float | None:
    start: datetime | None = row.started_at
    if start is None:
        return None
    end = row.completed_at or row.paused_at or utc_now()
    ran = (end - start).total_seconds() - (row.paused_seconds or 0.0)
    return round(max(ran, 0.0), 1)


def _uuid(value: str, field: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        msg = f"{field} must be a uuid, not {value!r}."
        raise ToolError(msg) from exc
