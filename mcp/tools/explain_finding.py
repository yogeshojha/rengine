"""One finding, with the evidence and the remediation, minus the noise."""

from __future__ import annotations

import re

from pydantic import Field

from mcp import links
from mcp.context import ToolContext
from mcp.dimensions import dimension
from mcp.errors import ToolError
from mcp.result import ToolResult
from mcp.tools._scope import resolve
from mcp.tools.base import Tool, ToolGroup, ToolInput
from shared.definitions.surface import SurfaceDimension

MAX_LOCATIONS = 25
MAX_EVIDENCE_CHARS = 1200
_FINGERPRINT = re.compile(r"^[0-9a-f]{64}$")
_CVE = re.compile(r"^CVE-\d{4}-\d{4,}$", re.IGNORECASE)


class Input(ToolInput):
    target: str = Field(description="The target the finding was reported on.")
    finding: str = Field(
        description=(
            "A template id, a check name, a CVE, or a finding fingerprint. "
            "Anything query_assets returned in template_id, template_name, "
            "cve_ids or fingerprint works."
        )
    )


class ExplainFinding(Tool):
    name = "explain_finding"
    title = "Explain finding"
    group = ToolGroup.EXPLAIN.value
    description = (
        "Everything reNgine knows about one finding: what the check tests for, why it "
        "matters, how to fix it, its CVE/CWE/CVSS/EPSS/KEV signals, every place it "
        "fires on this target, and the current triage decision. "
        "Use it after query_assets to turn a row into an explanation."
    )
    Input = Input
    examples = (
        "explain_finding target=example.com finding=CVE-2021-44228",
        "explain_finding target=example.com finding=apache-detect",
    )

    async def run(self, ctx: ToolContext, args: Input) -> ToolResult:
        from app.services.vulnerability import VulnerabilityService  # noqa: PLC0415

        dim = dimension(SurfaceDimension.VULNERABILITIES.value)
        scope = await resolve(ctx, args.target)
        scan_id = scope.require(dim)

        needle = args.finding.strip()
        query = _query_for(needle)
        f = dim.build_filter(query, limit=MAX_LOCATIONS, offset=0)
        page = await dim.search(ctx.session, scan_id, f, scope.project_id)

        if getattr(page, "error", None) or not page.items:
            msg = (
                f"No finding on {scope.target.target_value} matches {needle!r}. "
                "Use query_assets with dimension=vulnerabilities to list what is there."
            )
            raise ToolError(msg)

        service = VulnerabilityService(ctx.session)
        detail = await service.get(scan_id, page.items[0].id)
        if detail is None:
            msg = "That finding could not be loaded."
            raise ToolError(msg)

        locations = [
            {
                "matched_at": row.matched_at,
                "host": row.host,
                "ip": row.ip,
                "port": row.port,
                "state": row.state,
                "is_new": row.is_new,
            }
            for row in page.items
        ]

        return ToolResult(
            summary=(
                f"{detail.severity.upper()} — {detail.template_name} on "
                f"{scope.target.target_value}, {page.total} occurrence(s)"
            ),
            data={
                "check": {
                    "template_id": detail.template_id,
                    "name": detail.template_name,
                    "severity": detail.severity,
                    "scanner": detail.scanner,
                    "description": _trim(detail.description),
                    "impact": _trim(detail.impact),
                    "remediation": _trim(detail.remediation),
                    "references": (detail.references or [])[:8],
                    "tags": (detail.tags or [])[:12],
                },
                "risk": {
                    "cve_ids": detail.cve_ids or [],
                    "cwe_ids": detail.cwe_ids or [],
                    "cvss_score": detail.cvss_score,
                    "epss_score": detail.epss_score,
                    "epss_percentile": detail.epss_percentile,
                    "known_exploited": detail.is_kev,
                },
                "review": {"state": detail.state, "note": detail.note},
                "occurrences": page.total,
                "locations": locations,
                "evidence": {
                    "matched_at": detail.matched_at,
                    "extracted": (detail.extracted_results or [])[:10],
                    "curl": _trim(detail.curl_command, 600),
                },
            },
            pivot=links.scan_tab(
                ctx.ui_base_url, scan_id, dim.tab, f"template:{detail.template_id}"
            ),
            caveats=scope.caveat(dim),
            untrusted=True,
        )


def _query_for(needle: str) -> str:
    quoted = needle.replace('"', '\\"')
    if _FINGERPRINT.match(needle):
        return f'name:"{quoted}" or template:"{quoted}"'
    if _CVE.match(needle):
        return f'cve:"{quoted}"'
    return f'template:"{quoted}" or name:"{quoted}"'


def _trim(value: str | None, limit: int = MAX_EVIDENCE_CHARS) -> str | None:
    if not value:
        return None
    text = value.strip()
    return text if len(text) <= limit else text[:limit] + "…"
