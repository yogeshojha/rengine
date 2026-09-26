"""SPF, DMARC, DKIM, MTA-STS, DNSSEC and CAA per zone of a target."""

from __future__ import annotations

from pydantic import Field

from mcp import links
from mcp.context import ToolContext
from mcp.errors import ToolError
from mcp.result import ToolResult
from mcp.tools._scope import resolve
from mcp.tools.base import Tool, ToolGroup, ToolInput
from shared.definitions.domain_posture import CHECK_BY_KEY, SPF_ALL_LABELS
from shared.utils.text import counted

MAX_ZONES = 25


class Input(ToolInput):
    target: str = Field(description="The target whose zones to report.")
    failing_only: bool = Field(
        default=True, description="List only zones with a failing check."
    )


class DomainPosture(Tool):
    name = "domain_posture"
    title = "Domain posture"
    group = ToolGroup.INTERROGATE
    description = (
        "Sender, mail-transport and zone checks per registrable domain of a target, "
        "from its newest settled run: SPF policy and lookup count, DMARC policy and "
        "subdomain policy, DKIM selectors found, MTA-STS mode, TLS-RPT, DNSSEC and "
        "CAA. A zone failing a sender check can be forged as a sender. Checks a zone "
        "does not qualify for are absent, not passed."
    )
    Input = Input
    examples = ("domain_posture target=example.com",)

    async def run(self, ctx: ToolContext, args: Input) -> ToolResult:
        from app.services.domain_posture import DomainPostureService  # noqa: PLC0415

        scope = await resolve(ctx, args.target)
        summary = await DomainPostureService(ctx.session).for_target(
            scope.project_id, scope.target.id
        )
        if not summary.covered:
            msg = (
                f"Domain posture of {scope.target.target_value} has not been checked. "
                "Report it as not scanned, not as passing. Run a scan with the "
                "Domain posture stage enabled."
            )
            raise ToolError(msg)

        zones = [z for z in summary.zones if z.posture_issues or not args.failing_only]
        rows = [
            {
                "zone": z.zone,
                "under": z.parent,
                "web_assets": z.hosts,
                "spf": SPF_ALL_LABELS.get(z.spf_all or "", "none") if z.spf else "none",
                "spf_lookups": z.spf_lookups,
                "dmarc": z.dmarc_policy or "none",
                "dmarc_subdomains": z.dmarc_subdomain_policy,
                "dmarc_inherited": z.dmarc_inherited,
                "dkim_selectors": z.dkim_selectors,
                "dkim_key_bits": z.dkim_key_bits,
                "mail": "null MX" if z.null_mx else ("receives" if z.mx else "none"),
                "mta_sts": z.mta_sts_mode or ("published" if z.mta_sts else "none"),
                "tls_rpt": bool(z.tls_rpt),
                "dnssec": z.dnssec,
                "caa": z.caa,
                "failing": [key for key in z.posture_issues if key in CHECK_BY_KEY],
                "evidence": {k: v for k, v in z.evidence.items() if v},
            }
            for z in zones[:MAX_ZONES]
        ]

        checked = counted(summary.zone_count, "zone")
        if summary.mail_hosts:
            checked += f" and {counted(summary.mail_hosts, 'mail host')}"
        line = (
            f"{checked} checked for {scope.target.target_value}: "
            f"{summary.warning} with a warning, {summary.spoofable} spoofable, "
            f"{summary.clean} clean"
        )
        caveats = [
            f"Observed {summary.observed_at} by scan {summary.scan_id}.",
            "DKIM absence means no probed selector answered, not that no key exists.",
        ]
        if len(zones) > MAX_ZONES:
            caveats.append(f"{len(zones) - MAX_ZONES} further zones are not listed.")
        return ToolResult(
            summary=line,
            data={
                "target": scope.target.target_value,
                "scan_id": str(summary.scan_id),
                "zones_checked": summary.zone_count,
                "mail_hosts_checked": summary.mail_hosts,
                "warning": summary.warning,
                "info": summary.info,
                "clean": summary.clean,
                "spoofable": summary.spoofable,
                "checks": [
                    {
                        "check": c.key,
                        "label": CHECK_BY_KEY[c.key].label,
                        "tone": CHECK_BY_KEY[c.key].tone,
                        "failing": c.failing,
                        "applicable": c.applicable,
                        "fix": CHECK_BY_KEY[c.key].fix,
                    }
                    for c in summary.checks
                    if c.applicable
                ],
                "zones": rows,
            },
            pivot=links.target(ctx.ui_base_url, scope.target.id),
            caveats=caveats,
            untrusted=True,
        )
