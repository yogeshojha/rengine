from __future__ import annotations

from reports.analysis.engine import build_issues
from reports.base import RenderContext, Section
from reports.config import SectionConfig, choice, flag, limit, multi
from shared.definitions.compliance import FRAMEWORK_BY_KEY
from shared.definitions.reports import MAX_EVIDENCE_CHARS, SectionGroup
from shared.definitions.surface import SurfaceDimension
from shared.definitions.vulnerabilities import SEVERITY_ORDER, Severity
from shared.utils.text import strip_control


class FindingsDetailConfig(SectionConfig):
    group_by_issue: bool = flag(
        True,
        title="Group by weakness",
        description="One entry per check with every affected asset, instead of one entry per observation.",
    )
    severities: list[str] = multi(
        [s for s in SEVERITY_ORDER if s != Severity.UNKNOWN.value],
        title="Severities included",
        options={s: s.title() for s in SEVERITY_ORDER},
    )
    max_issues: int = limit(60, title="Weaknesses shown", minimum=1, maximum=500)
    max_assets: int = limit(
        25, title="Affected assets listed per weakness", minimum=1, maximum=500
    )
    show_description: bool = flag(True, title="Show description")
    show_impact: bool = flag(True, title="Show impact")
    show_remediation: bool = flag(True, title="Show remediation")
    show_references: bool = flag(True, title="Show references")
    show_evidence: bool = flag(True, title="Show request and response")
    show_curl: bool = flag(True, title="Show reproduction command")
    show_screenshot: bool = flag(False, title="Show a screenshot of the affected asset")
    show_controls: bool = flag(True, title="Show control mapping")
    show_classification: bool = flag(True, title="Show CVE, CWE, CVSS and EPSS")
    evidence_chars: int = limit(
        1200, title="Evidence characters kept", minimum=200, maximum=MAX_EVIDENCE_CHARS
    )
    order: str = choice(
        "risk",
        title="Order",
        options={
            "risk": "Risk score",
            "severity": "Severity",
            "count": "Times observed",
            "name": "Name",
        },
    )


class FindingsDetailSection(Section):
    name = "findings_detail"
    title = "Findings"
    description = "Every weakness with its evidence, affected assets and remediation."
    group = SectionGroup.FINDINGS.value
    requires = frozenset({SurfaceDimension.VULNERABILITIES.value})
    config_model = FindingsDetailConfig

    def build(self, ctx: RenderContext, cfg: FindingsDetailConfig) -> dict | None:
        issues = [i for i in build_issues(ctx.data) if i.severity in cfg.severities]
        if not issues:
            return None
        issues = _ordered(issues, cfg.order)[: cfg.max_issues]

        rows = []
        subs: list[tuple[str, str]] = []
        for index, issue in enumerate(issues):
            anchor = f"f-{index}-{issue.template_id.replace('/', '-')[:48]}"
            subs.append((issue.name, anchor))
            sample = issue.findings[0]
            rows.append(
                {
                    "issue": issue,
                    "anchor": anchor,
                    "sample": sample,
                    "assets": issue.findings[: cfg.max_assets],
                    "more": max(0, issue.count - cfg.max_assets),
                    "explainer": ctx.narrator.issue_explainer(issue),
                    "controls": _controls(issue) if cfg.show_controls else [],
                    "request": _clip(sample.request, cfg.evidence_chars)
                    if cfg.show_evidence
                    else "",
                    "response": _clip(sample.response, cfg.evidence_chars)
                    if cfg.show_evidence
                    else "",
                    "curl": _clip(sample.curl, 600) if cfg.show_curl else "",
                }
            )
        return {"rows": rows, "toc_subs": subs}


def _ordered(issues, key: str):
    if key == "severity":
        rank = {s: i for i, s in enumerate(SEVERITY_ORDER)}
        return sorted(issues, key=lambda i: (rank.get(i.severity, 9), -i.count))
    if key == "count":
        return sorted(issues, key=lambda i: -i.count)
    if key == "name":
        return sorted(issues, key=lambda i: i.name.lower())
    return issues


def _controls(issue) -> list[str]:
    out: list[str] = []
    for framework, controls in issue.controls.items():
        spec = FRAMEWORK_BY_KEY.get(framework)
        if not spec:
            continue
        lookup = spec.by_id
        for control in controls:
            found = lookup.get(control)
            label = f"{spec.name} {control}"
            out.append(f"{label} {found.title}" if found else label)
    return out[:6]


def _clip(value: str | None, length: int) -> str:
    if not value:
        return ""
    text = strip_control(value)
    return text if len(text) <= length else text[:length] + "\n… truncated"
