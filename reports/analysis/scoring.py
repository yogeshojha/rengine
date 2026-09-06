"""Posture and risk scores. Every deduction is named, so the number can be argued with."""

from __future__ import annotations

import math

from reports.analysis.brief import Posture
from reports.data.models import Issue
from shared.definitions.compliance import cwe_top_25_rank
from shared.definitions.vulnerabilities import EPSS_HIGH, Severity

_SEVERITY_WEIGHT = {
    Severity.CRITICAL.value: 100.0,
    Severity.HIGH.value: 60.0,
    Severity.MEDIUM.value: 25.0,
    Severity.LOW.value: 8.0,
    Severity.INFO.value: 1.0,
    Severity.UNKNOWN.value: 1.0,
}

# each rule is (label, per-item cost, ceiling)
_RULES = {
    "critical": ("Critical findings", 12.0, 36.0),
    "kev": ("Known exploited weaknesses", 10.0, 20.0),
    "high": ("High findings", 6.0, 24.0),
    "takeover": ("Subdomain takeover candidates", 9.0, 18.0),
    "origin": ("Origins reachable outside the CDN", 7.0, 14.0),
    "sensitive": ("Sensitive services exposed", 2.0, 12.0),
    "expired": ("Expired certificates on live hosts", 3.0, 9.0),
    "medium": ("Medium findings", 1.2, 10.0),
    "default_login": ("Default credentials", 10.0, 20.0),
}

_GRADES = ((90, "A"), (80, "B"), (70, "C"), (60, "D"), (45, "E"))


def grade_for(score: int) -> str:
    for floor, letter in _GRADES:
        if score >= floor:
            return letter
    return "F"


def posture(observations: dict[str, int]) -> Posture:
    total = 100.0
    deductions: list[dict] = []
    for key, count in observations.items():
        rule = _RULES.get(key)
        if not rule or not count:
            continue
        label, cost, ceiling = rule
        loss = min(count * cost, ceiling)
        total -= loss
        deductions.append({"label": label, "count": count, "points": round(loss, 1)})
    deductions.sort(key=lambda d: d["points"], reverse=True)
    score = max(0, min(100, round(total)))
    return Posture(score=score, grade=grade_for(score), deductions=deductions)


def issue_risk(issue: Issue) -> tuple[float, list[str]]:
    """Why one weakness outranks another of the same severity."""
    score = _SEVERITY_WEIGHT.get(issue.severity, 1.0)
    signals: list[str] = []

    if issue.is_kev:
        score *= 2.0
        signals.append("Known exploited")
    if issue.epss_score:
        score *= 1 + issue.epss_score
        if issue.epss_score >= EPSS_HIGH:
            signals.append(f"EPSS {issue.epss_score * 100:.0f}%")
    if issue.cvss_score:
        score *= 0.7 + issue.cvss_score / 10

    hosts = max(1, len(issue.hosts))
    score *= 1 + math.log10(hosts)
    if hosts > 1:
        signals.append(f"Affects {hosts} hosts")

    new = issue.new_count
    if new:
        score *= 1.15
        signals.append(
            "New since the previous run" if new == issue.count else f"{new} new"
        )

    rank = cwe_top_25_rank(issue.cwe_ids)
    if rank:
        score *= 1.1
        signals.append(f"CWE Top 25 (#{rank})")
    if issue.cve_ids:
        signals.append(
            issue.cve_ids[0]
            if len(issue.cve_ids) == 1
            else f"{len(issue.cve_ids)} CVEs"
        )

    return (round(score, 2), signals)


_EFFORT_RULES = (
    ({"default-login", "weak-password"}, "Credential change"),
    ({"config", "misconfig", "exposure", "files", "backup", "debug"}, "Configuration"),
    ({"cve", "outdated", "tech"}, "Patch or upgrade"),
    ({"takeover"}, "DNS change"),
    ({"ssl", "tls"}, "Certificate change"),
    ({"sqli", "xss", "rce", "ssti", "lfi", "ssrf", "injection"}, "Code change"),
)


def effort_for(tags: list[str]) -> str:
    lowered = {t.lower() for t in tags}
    for keys, label in _EFFORT_RULES:
        if lowered & keys:
            return label
    return "Investigate"
