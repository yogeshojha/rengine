"""Two runs of one target, and what moved between them."""

from __future__ import annotations

import uuid as _uuid

from pydantic import Field
from sqlalchemy import func
from sqlmodel import select

from mcp import links
from mcp.context import ToolContext
from mcp.result import ToolResult
from mcp.tools._scope import find_target
from mcp.tools.base import Tool, ToolGroup, ToolInput
from shared.definitions.compare import Comparability
from shared.enums.scan import SCAN_LIVE_STATUSES, ScanScope
from shared.models.scan import Scan

MAX_ROWS = 25
NEEDED_RUNS = 2


class Input(ToolInput):
    target: str | None = Field(
        default=None,
        description="A target, to compare its two most recent full runs.",
    )
    current: str | None = Field(
        default=None, description="The later run's scan id. Overrides target."
    )
    baseline: str | None = Field(
        default=None,
        description="The earlier run's scan id. Defaults to the run before `current`.",
    )
    dimension: str | None = Field(
        default=None,
        description="List the individual changes for one dimension rather than counts.",
    )


class CompareRuns(Tool):
    name = "compare_runs"
    title = "Compare runs"
    group = ToolGroup.INTERROGATE.value
    description = (
        "What changed between two runs of one target: what appeared, what changed "
        "and what disappeared, per result dimension. "
        "Read the comparability verdict before the numbers. Differences between "
        "runs that used different settings, or did different amounts of work, "
        "belong to the run rather than the target. A dimension one run did not "
        "scan reports as not covered, never as everything removed."
    )
    Input = Input
    examples = (
        "compare_runs target=example.com",
        "compare_runs target=example.com dimension=vulnerabilities",
    )

    async def run(self, ctx: ToolContext, args: Input) -> ToolResult:
        from app.services.scan_compare import ScanCompareService  # noqa: PLC0415

        service = ScanCompareService(ctx.session)
        current, baseline, project_id = await self._pick(ctx, args)
        report = await service.comparison(baseline, current, project_id)

        data = {
            "target": report.target_value,
            "baseline": {
                "scan_id": str(report.baseline.scan_id),
                "engine": report.baseline.engine_name,
                "started_at": report.baseline.started_at,
            },
            "current": {
                "scan_id": str(report.current.scan_id),
                "engine": report.current.engine_name,
                "started_at": report.current.started_at,
            },
            "comparability": report.comparability,
            "run_setup": [
                {
                    "what": row.label,
                    "baseline": row.baseline,
                    "current": row.current,
                    "material": row.material,
                }
                for row in report.run_diff
            ],
            "runs_between": report.runs_between,
            "dimensions": [
                {
                    "dimension": d.dimension,
                    "comparability": d.verdict.comparability,
                    "covered": d.verdict.covered_baseline and d.verdict.covered_current,
                    "appeared": d.appeared,
                    "changed": d.changed,
                    "disappeared": d.disappeared,
                    "unconfirmed": d.unconfirmed,
                    "unchanged": d.unchanged,
                    "was": d.total_baseline,
                    "now": d.total_current,
                }
                for d in report.dimensions
            ],
        }

        if args.dimension:
            rows = await service.rows(
                baseline_id=report.baseline.scan_id,
                current_id=report.current.scan_id,
                project_id=project_id,
                dimension=args.dimension,
                verbs=[],
                page=1,
                size=MAX_ROWS,
            )
            data["changes"] = [
                {
                    "verb": row.verb,
                    "signal": row.signal,
                    "asset": row.title,
                    "where": row.subtitle,
                    "severity": row.severity,
                    "fields": [
                        {"field": f.label, "was": f.before, "now": f.after}
                        for f in row.fields
                    ],
                }
                for row in rows.items
            ]
            data["changes_total"] = rows.total

        return ToolResult(
            summary=report.headline,
            data=data,
            pivot=links.compare(
                ctx.ui_base_url, report.current.scan_id, report.baseline.scan_id
            ),
            caveats=self._caveats(report),
            untrusted=True,
        )

    async def _pick(
        self, ctx: ToolContext, args: Input
    ) -> tuple[_uuid.UUID, _uuid.UUID | None, _uuid.UUID]:
        if args.current:
            current_id = _uuid.UUID(args.current)
            scan = await ctx.session.get(Scan, current_id)
            if scan is None:
                msg = f"No run with id {args.current}."
                raise ValueError(msg)
            ctx.check_project(scan.project_id)
            baseline = _uuid.UUID(args.baseline) if args.baseline else None
            return current_id, baseline, scan.project_id

        target = await find_target(ctx, args.target or "")
        started = func.coalesce(Scan.started_at, Scan.created_at)
        rows = (
            (
                await ctx.session.execute(
                    select(Scan)
                    .where(
                        Scan.target_id == target.id,
                        Scan.scope == ScanScope.FULL.value,
                        Scan.status.not_in(SCAN_LIVE_STATUSES),
                    )
                    .order_by(started.desc())
                    .limit(NEEDED_RUNS)
                )
            )
            .scalars()
            .all()
        )
        if len(rows) < NEEDED_RUNS:
            msg = (
                f"{target.target_value} has fewer than two finished full runs, "
                "so there is nothing to compare."
            )
            raise ValueError(msg)
        return rows[0].id, rows[1].id, target.project_id

    def _caveats(self, report) -> list[str]:
        out: list[str] = []
        if report.comparability != Comparability.LIKE_FOR_LIKE.value:
            out.append(
                "The two runs are not like for like. Read the per-dimension "
                "comparability before attributing any difference to the target."
            )
        material = [row for row in report.run_diff if row.material]
        if material:
            named = ", ".join(
                f"{row.label} {row.baseline or 'none'} → {row.current or 'none'}"
                for row in material[:4]
            )
            out.append(f"The runs were set up differently: {named}.")
        if report.runs_between:
            out.append(
                f"{report.runs_between} other run(s) of this target ran between these two. "
                "This is not what the previous run changed."
            )
        if report.suggestion is not None:
            out.append(
                "A like-for-like run exists: "
                f"{report.suggestion.engine_name} ({report.suggestion.scan_id}). "
                "Compare against that one for a cleaner answer."
            )
        for d in report.dimensions:
            if d.verdict.comparability == Comparability.NOT_COVERED.value:
                out.append(f"{d.label}: {d.verdict.note}")
            elif d.unconfirmed:
                out.append(
                    f"{d.label}: {d.unconfirmed} missing row(s) are unconfirmed "
                    "because the later run did not finish this dimension cleanly."
                )
            elif d.verdict.settings:
                out.append(f"{d.label}: {d.verdict.note}")
        if report.live:
            out.append(
                "The later run is still going. Missing rows are reported as unconfirmed."
            )
        return out
