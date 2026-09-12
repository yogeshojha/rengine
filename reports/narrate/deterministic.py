"""Prose written from the brief with no model."""

from __future__ import annotations

from reports.analysis.brief import ReportBrief
from reports.narrate.base import Narrator
from shared.definitions.surface import SURFACE_NOUN, SurfaceDimension
from shared.definitions.vulnerabilities import SEVERITY_LABELS

_DIM = SurfaceDimension


def _join(items: list[str], last: str = "and") -> str:
    values = [i for i in items if i]
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    return f"{', '.join(values[:-1])} {last} {values[-1]}"


def _count(value: int, noun: str, plural: str | None = None) -> str:
    word = noun if value == 1 else (plural or f"{noun}s")
    return f"{value:,} {word}"


class PlainNarrator(Narrator):
    ai_used = False

    def executive_summary(self, brief: ReportBrief) -> str:
        parts: list[str] = [self._opening(brief), self._position(brief)]
        paths = self._paths(brief)
        if paths:
            parts.append(paths)
        change = self._change(brief)
        if change:
            parts.append(change)
        first = self._first_action(brief)
        if first:
            parts.append(first)
        caveat = self._caveat(brief)
        if caveat:
            parts.append(caveat)
        return "\n\n".join(p for p in parts if p)

    def _opening(self, brief: ReportBrief) -> str:
        observed = (
            brief.observed_at.strftime("%d %B %Y")
            if brief.observed_at
            else "an unrecorded date"
        )
        covered = [
            SURFACE_NOUN[c["dimension"]][1]
            for c in brief.coverage
            if c["covered"] and c["dimension"] in SURFACE_NOUN
        ]
        scope = _join(covered) if covered else "no result dimensions"
        return (
            f"This report covers {brief.subject}, assessed on {observed}. "
            f"The run produced {scope}. {brief.headline}"
        )

    def _position(self, brief: ReportBrief) -> str:
        severity = brief.severity
        if not severity:
            covered = any(
                c["covered"]
                for c in brief.coverage
                if c["dimension"] == _DIM.VULNERABILITIES.value
            )
            if not covered:
                return "No vulnerability checks were run. This report describes the surface only."
            return "The checks that ran recorded no findings."
        ordered = [
            f"{severity[key]:,} {SEVERITY_LABELS[key].lower()}"
            for key in ("critical", "high", "medium", "low", "info")
            if severity.get(key)
        ]
        lead = f"The scan recorded {_join(ordered)} findings."
        posture = brief.posture
        detail = ""
        if posture.deductions:
            top = posture.deductions[0]
            detail = (
                f" The posture score is {posture.score} out of 100, grade {posture.grade}. "
                f"{top['label']} account for the largest deduction at {top['points']:.0f} points."
            )
        kev = brief.kev_count
        if kev:
            detail += (
                f" {_count(kev, 'weakness', 'weaknesses')} are on the CISA Known Exploited "
                "Vulnerabilities catalogue."
            )
        return lead + detail

    def _paths(self, brief: ReportBrief) -> str:
        if not brief.paths:
            return ""
        lines = [f"**{path.title}.** {path.detail}" for path in brief.paths[:3]]
        return "\n\n".join(lines)

    def _change(self, brief: ReportBrief) -> str:
        if brief.first_run:
            return "This is the first recorded run for this target. Nothing is reported as new."
        if not brief.changes:
            return "Nothing was added or retired since the previous run."
        pieces = []
        for line in brief.changes[:4]:
            noun = SURFACE_NOUN[line.dimension][1]
            bits = []
            if line.added:
                bits.append(f"{line.added:,} new")
            if line.gone:
                bits.append(f"{line.gone:,} no longer present")
            if bits:
                pieces.append(f"{_join(bits)} {noun}")
        return (
            f"Since the previous run the surface changed by {_join(pieces)}."
            if pieces
            else ""
        )

    def _first_action(self, brief: ReportBrief) -> str:
        if not brief.actions:
            return ""
        first = brief.actions[0]
        rest = len(brief.actions) - 1
        tail = (
            f" {_count(rest, 'further action')} {'follows' if rest == 1 else 'follow'} in the remediation plan."
            if rest > 0
            else ""
        )
        return (
            f"The first action addresses {first.title}. It clears "
            f"{_count(first.clears, 'observation')} across {_count(first.assets, 'asset')}.{tail}"
        )

    def _caveat(self, brief: ReportBrief) -> str:
        if not brief.caveats:
            return ""
        return "**Limitations.** " + " ".join(c.text for c in brief.caveats[:3])

    def risk_narrative(self, brief: ReportBrief) -> str:
        if not brief.risks:
            return ""
        top = brief.risks[:3]
        lines = [
            (
                f"{item.name} ranks first. It was observed {_count(item.count, 'time')} "
                f"across {_count(item.hosts, 'asset')}. Ranking signals: "
                + _join([s.lower() for s in item.signals] or ["severity"])
                + "."
            )
            if index == 0
            else (
                f"{item.name} follows with {_count(item.count, 'observation')} across "
                f"{_count(item.hosts, 'asset')}."
            )
            for index, item in enumerate(top)
        ]
        if brief.concentration:
            worst = brief.concentration[0]
            lines.append(
                f"Risk is concentrated on {worst.label}, with "
                f"{_count(worst.count, 'finding')} and a worst severity of {worst.worst.lower()}."
            )
        return " ".join(lines)

    def remediation_plan(self, brief: ReportBrief) -> str:
        if not brief.actions:
            return "No remediation is required from the findings in this report."
        return "Actions are ordered by the risk they remove."

    def surface_narrative(self, brief: ReportBrief) -> str:
        hosting = brief.hosting
        if not hosting.get("hosts"):
            return ""
        parts = [
            f"{_count(hosting['hosts'], 'web asset')} were catalogued. "
            f"{hosting['resolving']:,} resolve and {hosting['live']:,} answered a request."
        ]
        edge, cloud, direct = hosting["edge"], hosting["cloud"], hosting["direct"]
        if edge or cloud:
            parts.append(
                f"{edge:,} sit behind a CDN or WAF edge, {cloud:,} on cloud infrastructure "
                f"and {direct:,} answer directly from an origin."
            )
        if hosting.get("networks"):
            parts.append(f"The largest networks are {_join(hosting['networks'][:3])}.")
        if hosting.get("countries"):
            parts.append(f"Addresses resolve in {_join(hosting['countries'][:3])}.")
        exposure = brief.exposure
        if exposure.get("total"):
            parts.append(
                f"{_count(exposure['total'], 'service')} answered on "
                f"{_count(exposure['addresses'], 'address', 'addresses')}, "
                f"{exposure['web']:,} of them answering HTTP."
            )
            if exposure.get("sensitive"):
                parts.append(
                    f"{_count(exposure['sensitive'], 'service')} {'is' if exposure['sensitive'] == 1 else 'are'} administrative or data."
                )
        return " ".join(parts)
