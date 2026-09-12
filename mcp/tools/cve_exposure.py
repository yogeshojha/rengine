"""One CVE across the estate, counted on the evidence ladder."""

from __future__ import annotations

import re

from pydantic import Field

from mcp import links
from mcp.context import ToolContext
from mcp.errors import ToolError
from mcp.result import ToolResult
from mcp.tools._scope import find_target
from mcp.tools.base import Tool, ToolGroup, ToolInput

MAX_LOCATIONS = 50
_CVE = re.compile(r"^CVE-\d{4}-\d{4,7}$", re.IGNORECASE)


class Input(ToolInput):
    cve: str = Field(description="A CVE identifier, such as CVE-2021-44228.")
    target: str | None = Field(
        default=None,
        description=(
            "A target in reNgine. Names the project to answer for when the token "
            "reaches more than one."
        ),
    )


class CveExposure(Tool):
    name = "cve_exposure"
    title = "CVE exposure"
    group = ToolGroup.INTERROGATE.value
    description = (
        "Every asset in the estate that carries one CVE, across both findings "
        "dimensions, counted on one evidence ladder. Inferred: a version fell in "
        "the affected range. Observed: a check fired. Corroborated: two signals "
        "agree. Proven: an out-of-band artifact came back. Includes the NVD, EPSS "
        "and KEV record and how long the exposure has been held."
    )
    Input = Input
    examples = (
        "cve_exposure cve=CVE-2021-44228",
        "cve_exposure cve=CVE-2024-3400 target=example.com",
    )

    async def run(self, ctx: ToolContext, args: Input) -> ToolResult:
        from app.services.cve_exposure import CveExposureService  # noqa: PLC0415

        cve = args.cve.strip().upper()
        if not _CVE.match(cve):
            msg = f"{args.cve} is not a CVE identifier."
            raise ToolError(msg)
        project_id = await self._project(ctx, args.target)
        report = await CveExposureService(ctx.session).exposure(project_id, cve)

        ladder = {step.evidence: step.count for step in report.ladder}
        steps = " · ".join(f"{n} {name}" for name, n in ladder.items() if n)
        summary = (
            f"{cve}: {report.assets} asset(s) across {report.targets} target(s)"
            + (f" · {steps}" if steps else "")
            if report.assets
            else f"{cve}: no asset in this project carries it"
        )
        caveats = []
        if not report.corpus_ready:
            caveats.append("The NVD corpus is not loaded. Nothing is inferred.")
        if not report.finding_scans:
            caveats.append("No scan has run vulnerability checks in this project.")
        if report.suppressed:
            caveats.append(
                f"{report.suppressed} finding(s) set aside by a reviewer are not counted."
            )

        return ToolResult(
            summary=summary,
            data={
                "cve": cve,
                "record": {
                    "known": report.known,
                    "severity": report.severity,
                    "cvss_score": report.cvss_score,
                    "epss_score": report.epss_score,
                    "epss_percentile": report.epss_percentile,
                    "known_exploited": report.is_kev,
                    "ransomware": report.kev_ransomware,
                    "kev_due_date": report.kev_due_date,
                    "published_at": report.published_at,
                },
                "exposure": {
                    "assets": report.assets,
                    "targets": report.targets,
                    "software_rows": report.software_rows,
                    "finding_rows": report.finding_rows,
                    "first_seen": report.first_seen,
                    "ladder": [
                        {
                            "evidence": s.evidence,
                            "count": s.count,
                            "software": s.software,
                            "findings": s.findings,
                        }
                        for s in report.ladder
                    ],
                },
                "by_target": [
                    {
                        "target": t.target_value,
                        "assets": t.assets,
                        "software": t.software,
                        "findings": t.findings,
                        "first_seen": t.first_seen,
                    }
                    for t in report.by_target
                ],
                "locations": [
                    {
                        "host": loc.host,
                        "ip": loc.ip,
                        "port": loc.port,
                        "evidence": loc.evidence,
                        "basis": loc.basis,
                        "dimension": loc.dimension,
                        "state": loc.state,
                        "target": loc.target_value,
                        "first_seen": loc.discovered_at,
                    }
                    for loc in report.locations[:MAX_LOCATIONS]
                ],
                "locations_total": report.locations_total,
            },
            pivot=links.cve(ctx.ui_base_url, cve),
            caveats=caveats,
            untrusted=True,
        )

    @staticmethod
    async def _project(ctx: ToolContext, target: str | None):
        if target:
            return (await find_target(ctx, target)).project_id
        scoped = ctx.scoped_projects()
        if scoped:
            return scoped[0]
        msg = "This token reaches every project. Name a target to pick one."
        raise ToolError(msg)
