"""Resolve a target to the scans that answer for it."""

from __future__ import annotations

from pydantic import Field

from mcp import links
from mcp.context import ToolContext
from mcp.dimensions import DIMENSIONS
from mcp.phrasing import number, stamp
from mcp.result import ToolResult
from mcp.tools._scope import resolve
from mcp.tools.base import Tool, ToolGroup, ToolInput
from shared.utils.text import counted
from toolbox.base import fact, facts, hero


class Input(ToolInput):
    target: str = Field(
        description="A domain, IP address, CIDR range, URL or ASN added as a target."
    )


class ResolveTarget(Tool):
    name = "resolve_target"
    command = "target"
    value_field = "target"
    title = "Resolve target"
    group = ToolGroup.ORIENT
    description = (
        "For each of a target's five result dimensions: whether it was scanned, what "
        "the most recent covering scan found, when, and the scan id other tools take. "
        "Call this first. covered=false means not scanned, not zero."
    )
    Input = Input
    examples = ("resolve_target target=example.com",)

    async def run(self, ctx: ToolContext, args: Input) -> ToolResult:
        scope = await resolve(ctx, args.target)
        summary = scope.summary

        surface = []
        uncovered = []
        for dim in DIMENSIONS:
            found = scope.coverage(dim.key)
            entry = {
                "dimension": dim.key,
                "label": dim.label,
                "covered": found.covered,
                "count": found.value,
                "observed_at": found.observed_at,
                "scan_id": str(found.scan_id) if found.scan_id else None,
                "is_latest_scan": found.current,
            }
            metric = scope.metric(dim.key)
            if metric is not None:
                entry["added"] = metric.added
                entry["gone"] = metric.gone
                entry["previous"] = metric.previous
            if not found.covered:
                uncovered.append(dim.label)
            surface.append(entry)

        risk = summary.risk
        covered = [s for s in surface if s["covered"]]
        headline = (
            f"{scope.target.target_value}: "
            f"{len(covered)} of {len(surface)} dimensions scanned"
        )
        if risk.total:
            headline += f", {risk.actionable} findings need review"

        caveats = []
        if uncovered:
            caveats.append(
                "Not scanned: " + ", ".join(uncovered) + ". "
                "Report these as not scanned, not as zero."
            )
        if summary.scans_running:
            caveats.append(f"{counted(summary.scans_running, 'scan')} running now.")

        return ToolResult(
            summary=headline,
            data={
                "target": {
                    "id": str(scope.target.id),
                    "value": scope.target.target_value,
                    "type": getattr(
                        scope.target.target_type, "value", str(scope.target.target_type)
                    ),
                    "project_id": str(scope.project_id),
                },
                "surface": surface,
                "risk": {
                    "total": risk.total,
                    "actionable": risk.actionable,
                    "kev": risk.kev,
                    "suppressed": risk.suppressed,
                    "by_severity": [s.model_dump() for s in risk.by_severity],
                },
                "scans": {
                    "total": summary.scans_total,
                    "running": summary.scans_running,
                    "failed": summary.scans_failed,
                    "last_completed_at": summary.last_completed_at,
                },
                "sensitive_services": summary.sensitive_services,
                "monitored": summary.monitoring is not None,
            },
            pivot=links.target(ctx.ui_base_url, scope.target.id),
            caveats=caveats,
            blocks=_blocks(headline, surface, risk, summary),
        )


def _blocks(headline: str, surface: list[dict], risk, summary) -> list:
    severities = " · ".join(f"{s.label} {s.count}" for s in risk.by_severity if s.count)
    latest = max((s["observed_at"] for s in surface if s["observed_at"]), default=None)
    return [
        hero(headline, sub=f"Last observed {stamp(latest)}" if latest else None),
        facts(
            *[
                fact(s["label"], number(s["count"]) if s["covered"] else "not scanned")
                for s in surface
            ]
        ),
        facts(
            fact("Findings", number(risk.total)),
            fact("Need review", number(risk.actionable)),
            fact("KEV", number(risk.kev) if risk.kev else None),
            fact("Severity", severities or None),
            fact("Sensitive services", number(summary.sensitive_services) or None),
            fact(
                "Scans running",
                number(summary.scans_running) if summary.scans_running else None,
            ),
        ),
    ]
