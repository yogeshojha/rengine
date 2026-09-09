"""One CVE, ranked by the local feeds: how likely it is exploited, and whether it is already in use."""

from __future__ import annotations

import re

from pydantic import Field, field_validator
from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import array as pg_array

from shared.definitions.surface import SurfaceDimension
from shared.definitions.toolbox import (
    MAX_INPUT_LENGTH,
    Pivot,
    Tone,
    ToolExecution,
    ToolGroup,
)
from shared.definitions.vulnerabilities import EPSS_HIGH, Severity
from shared.models.threat_intel import CveIntel, EpssScore, KevEntry
from shared.models.vulnerability import Vulnerability
from toolbox.base import (
    Tool,
    ToolContext,
    ToolInput,
    ToolOutcome,
    cell,
    code,
    fact,
    facts,
    note,
    table,
    tag,
    tags,
)

CVE_PATTERN = re.compile(r"^CVE-\d{4}-\d{4,7}$", re.IGNORECASE)
MAX_POCS = 12

_SEVERITY_TONE = {
    Severity.CRITICAL.value: Tone.CRITICAL.value,
    Severity.HIGH.value: Tone.CRITICAL.value,
    Severity.MEDIUM.value: Tone.WARNING.value,
    Severity.LOW.value: Tone.INFO.value,
}


class Input(ToolInput):
    cve: str = Field(
        ...,
        min_length=1,
        max_length=MAX_INPUT_LENGTH,
        title="CVE identifier",
        description="CVE-2021-44228",
    )

    @field_validator("cve")
    @classmethod
    def _cve(cls, value: str) -> str:
        cleaned = value.strip().upper()
        if not CVE_PATTERN.match(cleaned):
            msg = f"{value} is not a CVE identifier."
            raise ValueError(msg)
        return cleaned


class CveLookup(Tool):
    name = "cve"
    title = "CVE"
    description = (
        "Exploitation likelihood, known-exploited status and published exploits."
    )
    group = ToolGroup.INTEL.value
    icon = "shield-alert"
    execution = ToolExecution.INLINE.value
    placeholder = "CVE-2021-44228"
    examples = ("CVE-2021-44228", "CVE-2014-0160")
    Input = Input

    async def run(self, ctx: ToolContext, args: Input) -> ToolOutcome:
        epss = await ctx.session.get(EpssScore, args.cve)
        kev = await ctx.session.get(KevEntry, args.cve)
        intel = await ctx.session.get(CveIntel, args.cve)
        findings = await _findings(ctx, args.cve)

        blocks = [
            facts(
                fact(
                    "Severity",
                    (intel.severity or "").title() if intel else "",
                    tone=_SEVERITY_TONE.get(
                        (intel.severity or "").lower() if intel else "",
                        Tone.NEUTRAL.value,
                    ),
                ),
                fact("CVSS", intel.cvss_score if intel else ""),
                fact(
                    "EPSS",
                    _pct(epss.score) if epss else "",
                    tone=Tone.CRITICAL.value
                    if epss and epss.score >= EPSS_HIGH
                    else Tone.NEUTRAL.value,
                    note=_rank(epss.percentile) if epss else None,
                ),
                fact(
                    "Known exploited",
                    "yes" if kev else "",
                    tone=Tone.CRITICAL.value,
                    note="CISA KEV",
                ),
                fact(
                    "Used by ransomware",
                    "yes" if kev and kev.known_ransomware else "",
                    tone=Tone.CRITICAL.value,
                ),
                fact(
                    "Published",
                    intel.published_at.date().isoformat()
                    if intel and intel.published_at
                    else "",
                ),
                title="Risk",
            ),
            facts(
                fact("Vendor", kev.vendor if kev else ""),
                fact("Product", kev.product if kev else ""),
                fact(
                    "Added to KEV",
                    kev.date_added.isoformat() if kev and kev.date_added else "",
                ),
                fact(
                    "Patch due",
                    kev.due_date.isoformat() if kev and kev.due_date else "",
                    tone=Tone.WARNING.value,
                ),
                fact("Required action", kev.required_action if kev else ""),
                title="CISA catalogue",
                empty="Not in the CISA known-exploited catalogue.",
            ),
            facts(
                fact(
                    "Nuclei template",
                    _template(intel),
                    tone=Tone.WARNING.value
                    if intel and intel.template_available is False
                    else Tone.NEUTRAL.value,
                ),
                fact("Remote", "yes" if intel and intel.is_remote else ""),
                fact(
                    "Needs authentication", "yes" if intel and intel.needs_auth else ""
                ),
                fact(
                    "Patch available", "yes" if intel and intel.patch_available else ""
                ),
                fact(
                    "Hosts exposed on the internet",
                    f"{intel.exposure_hosts:,}"
                    if intel and intel.exposure_hosts
                    else "",
                ),
                title="Exploitability",
                empty="No provider detail is cached for this CVE yet.",
            ),
            code(intel.description.strip(), title="Description")
            if intel and intel.description
            else None,
            tags(
                [tag(w) for w in (intel.weaknesses if intel else [])],
                title="Weaknesses",
                empty="No CWE mapping cached.",
            ),
            table(
                ["Exploit", "Source"],
                [_poc_row(p) for p in (intel.pocs if intel else [])[:MAX_POCS]],
                title="Published exploits",
                empty="No public exploit is cached for this CVE.",
                total=intel.poc_count if intel else 0,
            ),
        ]
        blocks = [b for b in blocks if b is not None]

        if epss is None and kev is None and intel is None:
            blocks.append(
                note(
                    "Nothing is held locally for this identifier. Either the exploitation feeds "
                    "have not been downloaded, or the CVE is not in them.",
                    tone=Tone.WARNING.value,
                )
            )

        caveats = []
        if intel is not None:
            caveats.append(
                "Severity, exploits and exposure counts are ProjectDiscovery's derived data, not reNgine's observations."
            )

        return ToolOutcome(
            summary=_summary(epss, kev, findings),
            blocks=blocks,
            caveats=caveats,
            pivot=Pivot(
                label="Open in Vulnerabilities",
                dimension=SurfaceDimension.VULNERABILITIES.value,
                query=f"cve:{args.cve}",
            )
            if findings
            else None,
            raw={
                "cve": args.cve,
                "epss": epss.model_dump(mode="json") if epss else None,
                "kev": kev.model_dump(mode="json") if kev else None,
                "intel": intel.model_dump(mode="json") if intel else None,
                "findings": findings,
            },
        )


NEAR_ONE = 0.999


def _pct(value: float) -> str:
    """Never round a 99.999% likelihood up to a certainty."""
    return "over 99.9%" if value >= NEAR_ONE else f"{value:.1%}"


def _rank(percentile: float) -> str:
    if percentile >= NEAR_ONE:
        return "in the top 0.1% of all CVEs"
    return f"higher than {percentile:.0%} of all CVEs"


def _template(intel: CveIntel | None) -> str:
    if intel is None or intel.template_available is None:
        return ""
    return "available" if intel.template_available else "none exists"


def _poc_row(poc) -> list:
    if isinstance(poc, dict):
        url = poc.get("url") or poc.get("link") or ""
        source = poc.get("source") or poc.get("type") or ""
    else:
        url, source = str(poc), ""
    return [cell(url, href=url or None, mono=True), cell(source, tone=Tone.MUTED.value)]


async def _findings(ctx: ToolContext, cve: str) -> int:
    if ctx.project_id is None:
        return 0
    return int(
        await ctx.session.scalar(
            select(func.count(Vulnerability.id)).where(
                Vulnerability.project_id == ctx.project_id,
                func.jsonb_exists_any(
                    cast(Vulnerability.cve_ids, JSONB), pg_array([cve])
                ),
            )
        )
        or 0
    )


def _summary(epss, kev, findings: int) -> str:
    parts = []
    if kev is not None:
        parts.append("Known exploited")
    if epss is not None:
        parts.append(f"EPSS {_pct(epss.score)}")
    if not parts:
        parts.append("Nothing held locally")
    if findings:
        parts.append(f"{findings} finding{'s' if findings != 1 else ''} here")
    return " · ".join(parts)
