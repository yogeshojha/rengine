"""Markdown and JSON exports, written from the brief rather than scraped from the HTML."""

from __future__ import annotations

import json

from reports.base import RenderContext
from shared.definitions.surface import SURFACE_LABELS, SURFACE_ORDER
from shared.definitions.vulnerabilities import SEVERITY_LABELS, SEVERITY_ORDER


def to_markdown(ctx: RenderContext) -> str:
    brief = ctx.brief
    lines: list[str] = [
        f"# {ctx.spec.title}",
        "",
        f"**Subject** {ctx.data.subject}  ",
        f"**Assessed** {ctx.data.observed_label}  ",
        f"**Report date** {ctx.now:%d %B %Y}",
        "",
        "## Executive summary",
        "",
        ctx.narrator.executive_summary(brief),
        "",
        "## Surface",
        "",
        "| Dimension | Observed | Previous |",
        "| --- | ---: | ---: |",
    ]
    for dimension in SURFACE_ORDER:
        entry = ctx.data.coverage[dimension]
        observed = f"{entry.count:,}" if entry.covered else "Not scanned"
        previous = f"{entry.previous:,}" if entry.previous is not None else "—"
        lines.append(f"| {SURFACE_LABELS[dimension]} | {observed} | {previous} |")

    if brief.severity:
        lines += [
            "",
            "## Findings by severity",
            "",
            "| Severity | Count |",
            "| --- | ---: |",
        ]
        for key in SEVERITY_ORDER:
            if brief.severity.get(key):
                lines.append(f"| {SEVERITY_LABELS[key]} | {brief.severity[key]:,} |")

    if brief.paths:
        lines += ["", "## Attack paths", ""]
        for path in brief.paths:
            lines += [f"### {path.title}", "", path.detail, ""]

    if brief.risks:
        lines += [
            "",
            "## Ranked weaknesses",
            "",
            "| # | Weakness | Severity | Seen | Hosts | Why |",
            "| ---: | --- | --- | ---: | ---: | --- |",
        ]
        for index, risk in enumerate(brief.risks, start=1):
            why = "; ".join(risk.signals) or "—"
            lines.append(
                f"| {index} | {risk.name} | {SEVERITY_LABELS.get(risk.severity, risk.severity)} "
                f"| {risk.count:,} | {risk.hosts:,} | {why} |"
            )

    if brief.actions:
        lines += [
            "",
            "## Remediation plan",
            "",
            "| # | Action | Severity | Change | Clears | Assets |",
            "| ---: | --- | --- | --- | ---: | ---: |",
        ]
        for index, action in enumerate(brief.actions, start=1):
            lines.append(
                f"| {index} | {action.title} | {SEVERITY_LABELS.get(action.severity, action.severity)} "
                f"| {action.effort} | {action.clears:,} | {action.assets:,} |"
            )

    if brief.caveats:
        lines += ["", "## Coverage and limitations", ""]
        lines += [f"- {c.text}" for c in brief.caveats]

    return "\n".join(lines) + "\n"


def to_json(ctx: RenderContext) -> str:
    brief = ctx.brief
    payload = {
        "title": ctx.spec.title,
        "subject": ctx.data.subject,
        "subject_type": ctx.data.subject_type,
        "scope": ctx.spec.scope,
        "generated_at": ctx.now.isoformat(),
        "observed_at": brief.observed_at.isoformat() if brief.observed_at else None,
        "posture": {
            "score": brief.posture.score,
            "grade": brief.posture.grade,
            "deductions": brief.posture.deductions,
        },
        "counts": brief.counts,
        "coverage": brief.coverage,
        "severity": brief.severity,
        "headline": brief.headline,
        "risks": [
            {
                "template_id": r.template_id,
                "name": r.name,
                "severity": r.severity,
                "observations": r.count,
                "hosts": r.hosts,
                "score": r.score,
                "signals": r.signals,
                "kev": r.kev,
                "cves": r.cves,
                "epss": r.epss,
                "cvss": r.cvss,
                "new": r.new,
            }
            for r in brief.risks
        ],
        "attack_paths": [
            {
                "key": p.key,
                "title": p.title,
                "detail": p.detail,
                "severity": p.severity,
                "count": p.count,
                "assets": p.assets,
                "evidence": p.evidence,
            }
            for p in brief.paths
        ],
        "actions": [
            {
                "title": a.title,
                "severity": a.severity,
                "effort": a.effort,
                "clears": a.clears,
                "assets": a.assets,
                "templates": a.templates,
                "controls": a.controls,
            }
            for a in brief.actions
        ],
        "changes": [
            {
                "dimension": c.dimension,
                "added": c.added,
                "gone": c.gone,
                "added_sample": c.added_sample,
                "gone_sample": c.gone_sample,
            }
            for c in brief.changes
        ],
        "compliance": brief.compliance,
        "exposure": brief.exposure,
        "hosting": brief.hosting,
        "caveats": [{"kind": c.kind, "text": c.text} for c in brief.caveats],
    }
    return json.dumps(payload, indent=2, default=str)
