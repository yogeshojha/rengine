"""Turn a source into a brief. Everything the report claims is decided here, once."""

from __future__ import annotations

from reports.analysis.brief import (
    Action,
    Caveat,
    ChangeLine,
    Concentration,
    Highlight,
    ReportBrief,
)
from reports.analysis.narratives import attack_paths
from reports.analysis.scoring import effort_for, issue_risk, posture
from reports.data.models import Issue
from reports.data.source import ReportSource
from shared.definitions.compliance import (
    FRAMEWORK_BY_KEY,
    SURFACE_CONTROLS,
    cwe_top_25_rank,
    map_finding,
)
from shared.definitions.ports import ServiceClass
from shared.definitions.surface import (
    SURFACE_LABELS,
    SURFACE_NOUN,
    SURFACE_ORDER,
    SurfaceDimension,
)
from shared.definitions.vulnerabilities import (
    SEVERITY_LABELS,
    SEVERITY_ORDER,
    Severity,
    severity_rank,
)

_DIM = SurfaceDimension
_MAX_ACTIONS = 12
_MAX_RISKS = 25


def build_issues(source: ReportSource) -> list[Issue]:
    grouped: dict[str, Issue] = {}
    for finding in source.findings:
        issue = grouped.get(finding.template_id)
        if issue is None:
            issue = Issue(
                template_id=finding.template_id,
                name=finding.name,
                severity=finding.severity,
                scanner=finding.scanner,
                protocol=finding.protocol,
                description=finding.description,
                impact=finding.impact,
                remediation=finding.remediation,
                references=list(finding.references),
                tags=list(finding.tags),
                cve_ids=list(finding.cve_ids),
                cwe_ids=list(finding.cwe_ids),
                cvss_score=finding.cvss_score,
                epss_score=finding.epss_score,
                is_kev=finding.is_kev,
            )
            issue.controls = map_finding(finding.cwe_ids, finding.tags)
            issue.cwe_rank = cwe_top_25_rank(finding.cwe_ids)
            grouped[finding.template_id] = issue
        issue.findings.append(finding)
        if severity_rank(finding.severity) < severity_rank(issue.severity):
            issue.severity = finding.severity

    for issue in grouped.values():
        issue.risk = issue_risk(issue)[0]
    return sorted(grouped.values(), key=lambda i: (-i.risk, severity_rank(i.severity)))


def _observations(source: ReportSource, issues: list[Issue], paths) -> dict[str, int]:
    keyed = {p.key: p for p in paths}
    severity = source.severity_counts
    live = {h.name for h in source.host_rows if h.status}
    return {
        "critical": severity.get(Severity.CRITICAL.value, 0),
        "high": severity.get(Severity.HIGH.value, 0),
        "medium": severity.get(Severity.MEDIUM.value, 0),
        "kev": sum(1 for i in issues if i.is_kev),
        "takeover": keyed["takeover"].count if "takeover" in keyed else 0,
        "origin": keyed["origin_exposed"].count if "origin_exposed" in keyed else 0,
        "default_login": keyed["default_credentials"].count
        if "default_credentials" in keyed
        else 0,
        "sensitive": len([s for s in source.sensitive_services if not s.is_http]),
        "expired": len(
            [
                c
                for c in source.certificates
                if c.expired and (not live or c.host in live)
            ]
        ),
    }


def _actions(issues: list[Issue]) -> list[Action]:
    out: list[Action] = []
    for issue in issues:
        if issue.severity in {Severity.INFO.value, Severity.UNKNOWN.value}:
            continue
        controls = issue.controls.get("owasp_top10", [])
        remediation = (issue.remediation or "").strip()
        detail = (
            remediation.split("\n")[0][:300]
            if remediation
            else (
                f"Review every affected asset and remove the condition {issue.name} reports."
            )
        )
        out.append(
            Action(
                title=issue.name,
                detail=detail,
                severity=issue.severity,
                effort=effort_for(issue.tags),
                clears=issue.count,
                assets=len(issue.hosts),
                templates=[issue.template_id],
                controls=controls,
            )
        )
        if len(out) >= _MAX_ACTIONS:
            break
    return out


def _changes(source: ReportSource) -> list[ChangeLine]:
    if source.previous_scan is None:
        return []
    lines: list[ChangeLine] = []
    for dimension in SURFACE_ORDER:
        if not source.coverage[dimension].covered:
            continue
        added, gone, added_total, gone_total = source.added_and_gone(
            dimension, limit=12
        )
        if not added_total and not gone_total:
            continue
        lines.append(
            ChangeLine(
                dimension=dimension,
                added=added_total,
                gone=gone_total,
                baseline=source.has_baseline(dimension),
                added_sample=added,
                gone_sample=gone,
            )
        )
    return lines


def _concentration(source: ReportSource, issues: list[Issue]) -> list[Concentration]:
    del issues
    rows = sorted(
        ((host, data) for host, data in source.findings_by_host.items()),
        key=lambda item: (-item[1][0], severity_rank(item[1][1])),
    )[:8]
    return [
        Concentration(
            label=host,
            count=count,
            worst=SEVERITY_LABELS.get(worst, "Unknown"),
            note="",
        )
        for host, (count, worst) in rows
    ]


def _caveats(source: ReportSource) -> list[Caveat]:
    out: list[Caveat] = []
    for dimension in SURFACE_ORDER:
        entry = source.coverage[dimension]
        if not entry.covered:
            out.append(
                Caveat(
                    kind="not_scanned",
                    text=(
                        f"{SURFACE_LABELS[dimension]} were not assessed. "
                        "No conclusion about them can be drawn from this report."
                    ),
                )
            )
    for row in source.coverage_rows:
        if row.status == "partial":
            out.append(
                Caveat(
                    kind="partial",
                    text=(
                        f"The {row.group} scanner run finished partially. "
                        f"{row.hosts_scanned or 0} of {row.hosts_total} hosts were covered."
                    ),
                )
            )
        elif row.status == "failed":
            out.append(
                Caveat(
                    kind="failed",
                    text=f"The {row.group} scanner run failed: {row.error or 'no reason recorded'}.",
                )
            )
        if row.hosts_dropped:
            out.append(
                Caveat(
                    kind="dropped",
                    text=f"{len(row.hosts_dropped)} hosts were dropped by the scanner budget and were not checked.",
                )
            )
    if source.scan is not None and source.scan.status == "cancelled":
        out.append(
            Caveat(
                kind="cancelled",
                text="This run was cancelled. It reports what had been written when it stopped, and is not a complete pass.",
            )
        )
    if source.suppressed_count:
        out.append(
            Caveat(
                kind="suppressed",
                text=f"{source.suppressed_count} findings are hidden because a reviewer marked them as accepted or false positive.",
            )
        )
    excluded = source.excluded()
    if any(excluded.values()):
        parts = [f"{len(v)} {k}" for k, v in excluded.items() if v]
        out.append(Caveat(kind="scope", text=f"The scope excluded {', '.join(parts)}."))
    seen: set[str] = set()
    return [c for c in out if not (c.text in seen or seen.add(c.text))]


def _compliance(issues: list[Issue], covered: frozenset[str]) -> dict:
    out: dict[str, dict] = {}
    for key, framework in FRAMEWORK_BY_KEY.items():
        counts: dict[str, int] = {}
        for issue in issues:
            for control in issue.controls.get(key, []):
                counts[control] = counts.get(control, 0) + issue.count
        surface = SURFACE_CONTROLS.get(key, ()) if covered else ()
        if not counts and not surface:
            continue
        out[key] = {
            "name": framework.name,
            "version": framework.version,
            "counts": counts,
            "evidence_only": list(surface),
        }
    return out


def _highlights(source: ReportSource, brief: ReportBrief) -> list[Highlight]:
    out: list[Highlight] = []
    for dimension in SURFACE_ORDER:
        entry = source.coverage[dimension]
        noun = SURFACE_NOUN[dimension][1]
        if not entry.covered:
            out.append(
                Highlight(
                    key=dimension,
                    label=SURFACE_LABELS[dimension],
                    value="Not scanned",
                    detail=f"No run has produced {noun} for this target.",
                    tone="absent",
                )
            )
            continue
        detail = ""
        if entry.previous is not None:
            delta = entry.count - entry.previous
            if delta > 0:
                detail = f"{delta} more than the previous run"
            elif delta < 0:
                detail = f"{abs(delta)} fewer than the previous run"
            else:
                detail = "unchanged"
        out.append(
            Highlight(
                key=dimension,
                label=SURFACE_LABELS[dimension],
                value=f"{entry.count:,}",
                detail=detail,
                tone="neutral",
            )
        )
    del brief
    return out


def _headline(brief: ReportBrief) -> str:
    severity = brief.severity
    if brief.kev_count:
        return (
            f"{brief.kev_count} weakness{'es' if brief.kev_count != 1 else ''} with "
            "confirmed exploitation in the wild are present on this surface."
        )
    if severity.get(Severity.CRITICAL.value):
        count = severity[Severity.CRITICAL.value]
        return f"{count} critical finding{'s' if count != 1 else ''} require immediate attention."
    if severity.get(Severity.HIGH.value):
        count = severity[Severity.HIGH.value]
        return (
            f"{count} high severity finding{'s' if count != 1 else ''} were identified."
        )
    if brief.paths:
        return brief.paths[0].title + "."
    if brief.counts.get(
        _DIM.VULNERABILITIES.value
    ) == 0 and _DIM.VULNERABILITIES.value in {
        c["dimension"] for c in brief.coverage if c["covered"]
    }:
        return "No actionable weaknesses were identified in the checks that ran."
    return f"{brief.counts.get(_DIM.WEB_ASSETS.value, 0):,} assets were catalogued on this surface."


def build_brief(source: ReportSource) -> ReportBrief:
    issues = build_issues(source)
    paths = attack_paths(source, issues)

    counts = {d: source.count_of(d) for d in SURFACE_ORDER}
    coverage = [
        {
            "dimension": d,
            "label": SURFACE_LABELS[d],
            "covered": source.coverage[d].covered,
            "count": source.coverage[d].count,
            "previous": source.coverage[d].previous,
        }
        for d in SURFACE_ORDER
    ]

    brief = ReportBrief(
        subject=source.subject,
        subject_type=source.subject_type,
        scope=source.scope,
        observed_at=source.observed_at,
        engine=source.scan.engine_name if source.scan else "",
        duration_seconds=(
            (source.scan.completed_at - source.scan.started_at).total_seconds()
            if source.scan and source.scan.completed_at and source.scan.started_at
            else None
        ),
        counts=counts,
        coverage=coverage,
        severity={k: v for k, v in source.severity_counts.items() if v},
        paths=paths,
        suppressed=source.suppressed_count,
        first_run=source.previous_scan is None,
    )

    brief.posture = posture(_observations(source, issues, paths))
    brief.risks = []
    for issue in issues[:_MAX_RISKS]:
        score, signals = issue_risk(issue)
        brief.risks.append(_risk_item(issue, score, signals))
    brief.actions = _actions(issues)
    brief.caveats = _caveats(source)
    brief.changes = _changes(source)
    brief.concentration = _concentration(source, issues)
    brief.compliance = _compliance(issues, source.covered_dimensions)
    brief.exposure = _exposure(source)
    brief.hosting = _hosting(source)
    brief.highlights = _highlights(source, brief)
    brief.headline = _headline(brief)
    return brief


def _risk_item(issue: Issue, score: float, signals: list[str]):
    from reports.analysis.brief import RiskItem  # noqa: PLC0415

    return RiskItem(
        template_id=issue.template_id,
        name=issue.name,
        severity=issue.severity,
        count=issue.count,
        hosts=len(issue.hosts),
        score=score,
        signals=signals,
        kev=issue.is_kev,
        epss=issue.epss_score,
        cvss=issue.cvss_score,
        cves=list(issue.cve_ids),
        sample=issue.findings[0].matched_at if issue.findings else "",
        new=issue.new_count,
    )


def _exposure(source: ReportSource) -> dict:
    services = source.service_rows
    if not services:
        return {}
    web = sum(1 for s in services if s.is_http)
    classes = {f.name: f.count for f in source.service_classes}
    return {
        "total": len(services),
        "web": web,
        "non_web": len(services) - web,
        "sensitive": len(source.sensitive_services),
        "classes": classes,
        "addresses": len({s.ip for s in services}),
        "top": [f.name for f in source.top_services[:6]],
        "database": classes.get(ServiceClass.DATABASE.value, 0),
        "remote": classes.get(ServiceClass.REMOTE.value, 0),
    }


def _hosting(source: ReportSource) -> dict:
    edge, cloud, direct = source.cdn_split
    hosts = source.host_rows
    resolving = sum(1 for h in hosts if h.ips or h.status)
    return {
        "hosts": len(hosts),
        "resolving": resolving,
        "live": sum(1 for h in hosts if h.status),
        "edge": edge,
        "cloud": cloud,
        "direct": direct,
        "networks": [f.name for f in source.networks[:5]],
        "countries": [f.name for f in source.countries[:5]],
        "waf": sum(1 for h in hosts if h.waf),
    }


SEVERITY_SEQUENCE = SEVERITY_ORDER
