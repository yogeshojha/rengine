"""New since last time, across every target in the project."""

from __future__ import annotations

from pydantic import Field

from mcp import links
from mcp.context import ToolContext
from mcp.result import ToolResult
from mcp.tools._scope import project_for
from mcp.tools.base import Tool, ToolGroup, ToolInput
from shared.definitions.dashboard import DEFAULT_WINDOW, WINDOW_DELTAS

MAX_ROWS = 30
WINDOWS = tuple(WINDOW_DELTAS)


class Input(ToolInput):
    window: str = Field(
        default=DEFAULT_WINDOW,
        description=f"How far back to look. One of: {', '.join(WINDOWS)}.",
    )
    project_id: str | None = Field(
        default=None,
        description="Project to report on. Omit when the token is scoped to one.",
    )


class WhatChanged(Tool):
    name = "what_changed"
    title = "What changed"
    group = ToolGroup.INTERROGATE.value
    description = (
        "What is new across every target in a project over a window: new web assets, "
        "services, endpoints, addresses and findings, per target, plus targets that "
        "have never been scanned or have gone stale. "
        "Counts only items a scan was the first to report, and only where an earlier "
        "scan gives a baseline, so a target's first scan never reports everything as new."
    )
    Input = Input
    examples = ("what_changed window=7d",)

    async def run(self, ctx: ToolContext, args: Input) -> ToolResult:
        import uuid as _uuid  # noqa: PLC0415

        from app.services.dashboard_overview import (  # noqa: PLC0415
            DashboardOverviewService,
        )

        window = args.window if args.window in WINDOWS else DEFAULT_WINDOW
        project_id = await project_for(
            ctx, _uuid.UUID(args.project_id) if args.project_id else None
        )
        overview = await DashboardOverviewService(ctx.session).overview(
            project_id, window
        )

        changes = [
            {
                "target": row.target_value,
                "type": row.target_type,
                "runs": row.runs,
                "last_scan_at": row.last_at,
                "last_status": row.last_status,
                "new": {k: v for k, v in (row.new or {}).items() if v},
                "first_time_covered": list(row.first or []),
                "web_assets_gone": row.gone_web_assets,
            }
            for row in overview.changes[:MAX_ROWS]
            if (row.new and any((row.new or {}).values()))
            or row.first
            or row.gone_web_assets
        ]

        risk = overview.risk
        headline = (
            f"{len(changes)} target(s) changed in the last {window}"
            if changes
            else f"Nothing new in the last {window}"
        )

        caveats = []
        if overview.targets_never_scanned:
            caveats.append(
                f"{overview.targets_never_scanned} target(s) have never been scanned."
            )
        if overview.targets_stale:
            caveats.append(f"{overview.targets_stale} target(s) have a stale last run.")
        if overview.failed_in_window:
            caveats.append(f"{overview.failed_in_window} run(s) failed in this window.")

        return ToolResult(
            summary=headline,
            data={
                "window": window,
                "generated_at": overview.generated_at,
                "targets": {
                    "total": overview.targets_total,
                    "scanned": overview.targets_scanned,
                    "never_scanned": overview.targets_never_scanned,
                    "stale": overview.targets_stale,
                    "monitored": overview.targets_monitored,
                },
                "risk": risk.model_dump(mode="json") if risk else None,
                "changes": changes,
            },
            pivot=links.dashboard(ctx.ui_base_url),
            caveats=caveats,
        )
