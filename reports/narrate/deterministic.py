"""Prose written from the brief with no model. This is what an instance without AI reads."""

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
            else "an earlier date"
        )
        covered = [c["label"] for c in brief.coverage if c["covered"]]
        scope = _join(covered).lower() if covered else "no result dimensions"
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
                return (
                    "No vulnerability checks were run, so this report makes no statement "
                    "about weaknesses. It describes the surface that exists."
                )
            return (
                "No findings were recorded by the checks that ran. That is a statement "
                "about the checks selected. It is not a guarantee about the estate."
            )
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
                f" {_count(kev, 'weakness', 'weaknesses')} appear on the CISA Known Exploited "
                "Vulnerabilities catalog, which means exploitation has been observed in the wild."
            )
        return lead + detail

    def _paths(self, brief: ReportBrief) -> str:
        if not brief.paths:
            return ""
        lines = [f"**{path.title}.** {path.detail}" for path in brief.paths[:3]]
        return "\n\n".join(lines)

    def _change(self, brief: ReportBrief) -> str:
        if brief.first_run:
            return (
                "This is the first run recorded for this target, so nothing is reported "
                "as new. The next run will compare against this one."
            )
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
            f" A further {_count(rest, 'action')} follow in the remediation plan."
            if rest > 0
            else ""
        )
        return (
            f"The first action addresses {first.title}. It clears "
            f"{_count(first.clears, 'observation')} across {_count(first.assets, 'asset')} "
            f"and is rated {first.effort.lower()} effort.{tail}"
        )

    def _caveat(self, brief: ReportBrief) -> str:
        if not brief.caveats:
            return ""
        return "**Scope of this statement.** " + " ".join(
            c.text for c in brief.caveats[:3]
        )

    def risk_narrative(self, brief: ReportBrief) -> str:
        if not brief.risks:
            return ""
        top = brief.risks[:3]
        lines = [
            (
                f"{item.name} ranks first because "
                + _join(
                    [s.lower() for s in item.signals]
                    or ["it is the most severe check that fired"]
                )
                + f". It was observed {_count(item.count, 'time')} across {_count(item.hosts, 'host')}."
            )
            if index == 0
            else (
                f"{item.name} follows, {_count(item.count, 'observation')} across "
                f"{_count(item.hosts, 'host')}."
            )
            for index, item in enumerate(top)
        ]
        if brief.concentration:
            worst = brief.concentration[0]
            lines.append(
                f"Risk is concentrated on {worst.label}, which carries "
                f"{_count(worst.count, 'finding')} with {worst.worst.lower()} as the worst."
            )
        return " ".join(lines)

    def remediation_plan(self, brief: ReportBrief) -> str:
        if not brief.actions:
            return "No remediation is required from the findings in this report."
        return (
            "Actions are ordered by the risk they remove, not by severity alone. "
            "An action that clears many observations on many assets outranks a single "
            "finding of the same severity."
        )

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
                    f"{_count(exposure['sensitive'], 'service')} are of a kind that "
                    "normally belongs on a private network."
                )
        return " ".join(parts)
