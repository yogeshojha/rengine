"""New since last time, across every target in the project."""

from __future__ import annotations

from pydantic import Field

from mcp import links
from mcp.context import ToolContext
from mcp.phrasing import number, stamp
from mcp.result import ToolResult
from mcp.tools._args import optional_uuid
from mcp.tools._scope import project_for
from mcp.tools.base import Tool, ToolGroup, ToolInput
from shared.definitions.dashboard import DEFAULT_WINDOW, WINDOW_DELTAS
from shared.utils.text import counted
from toolbox.base import cell, fact, facts, hero, table

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
    command = "changes"
    value_field = "window"
    title = "What changed"
    group = ToolGroup.INTERROGATE
    description = (
        "New web assets, services, endpoints, addresses and findings per target over "
        "a window, plus targets not scanned or stale. Counts items first reported in "
        "the window against an earlier baseline. A target's first scan reports "
        "nothing as new."
    )
    Input = Input
    examples = ("what_changed window=7d",)

    async def run(self, ctx: ToolContext, args: Input) -> ToolResult:
        from app.services.dashboard_overview import (  # noqa: PLC0415
            DashboardOverviewService,
        )

        window = args.window if args.window in WINDOWS else DEFAULT_WINDOW
        project_id = await project_for(
            ctx, optional_uuid(args.project_id, "project_id")
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
            f"{counted(len(changes), 'target')} changed in the last {window}"
            if changes
            else f"Nothing new in the last {window}"
        )

        caveats = []
        if overview.targets_never_scanned:
            caveats.append(
                f"{counted(overview.targets_never_scanned, 'target')} not scanned."
            )
        if overview.targets_stale:
            caveats.append(
                f"{counted(overview.targets_stale, 'target')} have a stale last run."
            )
        if overview.failed_in_window:
            caveats.append(
                f"{counted(overview.failed_in_window, 'run')} failed in this window."
            )

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
            blocks=_blocks(headline, overview, risk, changes),
        )


def _change_line(row: dict) -> str:
    parts = [f"{k.replace('_', ' ')} +{v}" for k, v in row["new"].items()]
    if row["first_time_covered"]:
        parts.append("first: " + ", ".join(row["first_time_covered"]))
    if row["web_assets_gone"]:
        parts.append(f"web assets gone {row['web_assets_gone']}")
    return " · ".join(parts)


def _blocks(headline: str, overview, risk, changes: list[dict]) -> list:
    tiers = dict(getattr(risk, "tiers", None) or {})
    return [
        hero(headline),
        facts(
            fact("Targets", number(overview.targets_total)),
            fact("Scanned", number(overview.targets_scanned)),
            fact("Never scanned", number(overview.targets_never_scanned) or None),
            fact("Findings", number(risk.total) if risk else None),
            fact("Act now", number(tiers.get("act")) if tiers.get("act") else None),
            fact("KEV", number(risk.kev) if risk and risk.kev else None),
        ),
        table(
            ["Target", "Last run", "Change"],
            [
                [
                    cell(row["target"], mono=True),
                    cell(f"{row['last_status']} {stamp(row['last_scan_at'])}"),
                    cell(_change_line(row)),
                ]
                for row in changes
            ],
            title="Changes",
            empty="No changes.",
        ),
    ]
