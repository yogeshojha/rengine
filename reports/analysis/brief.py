"""The brief: every fact the document argues from, small enough to hand to a model."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime

from shared.definitions.ai import MAX_BRIEF_BYTES


@dataclass
class Posture:
    score: int = 100
    grade: str = "A"
    verdict: str = ""
    deductions: list[dict] = field(default_factory=list)


@dataclass
class RiskItem:
    template_id: str
    name: str
    severity: str
    count: int
    hosts: int
    score: float
    signals: list[str] = field(default_factory=list)
    kev: bool = False
    epss: float | None = None
    cvss: float | None = None
    cves: list[str] = field(default_factory=list)
    sample: str = ""
    new: int = 0


@dataclass
class AttackPath:
    key: str
    title: str
    detail: str
    severity: str
    evidence: list[str] = field(default_factory=list)
    assets: list[str] = field(default_factory=list)
    count: int = 0


@dataclass
class Action:
    title: str
    detail: str
    severity: str
    effort: str
    clears: int
    assets: int
    templates: list[str] = field(default_factory=list)
    controls: list[str] = field(default_factory=list)


@dataclass
class Caveat:
    kind: str
    text: str


@dataclass
class Concentration:
    label: str
    count: int
    worst: str = ""
    note: str = ""


@dataclass
class ChangeLine:
    dimension: str
    added: int = 0
    gone: int = 0
    baseline: bool = True
    added_sample: list[str] = field(default_factory=list)
    gone_sample: list[str] = field(default_factory=list)


@dataclass
class Highlight:
    key: str
    label: str
    value: str
    detail: str = ""
    tone: str = "neutral"


@dataclass
class ReportBrief:
    subject: str
    subject_type: str
    scope: str
    observed_at: datetime | None = None
    engine: str = ""
    duration_seconds: float | None = None
    counts: dict[str, int] = field(default_factory=dict)
    coverage: list[dict] = field(default_factory=list)
    severity: dict[str, int] = field(default_factory=dict)
    posture: Posture = field(default_factory=Posture)
    risks: list[RiskItem] = field(default_factory=list)
    paths: list[AttackPath] = field(default_factory=list)
    actions: list[Action] = field(default_factory=list)
    caveats: list[Caveat] = field(default_factory=list)
    changes: list[ChangeLine] = field(default_factory=list)
    concentration: list[Concentration] = field(default_factory=list)
    highlights: list[Highlight] = field(default_factory=list)
    exposure: dict = field(default_factory=dict)
    hosting: dict = field(default_factory=dict)
    compliance: dict = field(default_factory=dict)
    headline: str = ""
    suppressed: int = 0
    first_run: bool = True

    @property
    def actionable(self) -> int:
        return sum(self.severity.get(k, 0) for k in ("critical", "high", "medium"))

    @property
    def kev_count(self) -> int:
        return sum(1 for r in self.risks if r.kev)

    def prompt_payload(self, *, limit: int = 14) -> dict:
        """The bounded slice a model is allowed to see. No rows, no evidence, no secrets."""
        return {
            "subject": self.subject,
            "subject_type": self.subject_type,
            "observed": self.observed_at.strftime("%Y-%m-%d")
            if self.observed_at
            else None,
            "first_run": self.first_run,
            "counts": self.counts,
            "coverage": self.coverage,
            "severity": {k: v for k, v in self.severity.items() if v},
            "posture": {
                "score": self.posture.score,
                "grade": self.posture.grade,
                "deductions": self.posture.deductions[:8],
            },
            "top_risks": [
                {
                    "name": r.name,
                    "severity": r.severity,
                    "observations": r.count,
                    "hosts": r.hosts,
                    "kev": r.kev,
                    "epss": round(r.epss, 3) if r.epss else None,
                    "cves": r.cves[:3],
                    "signals": r.signals[:4],
                }
                for r in self.risks[:limit]
            ],
            "attack_paths": [
                {
                    "title": p.title,
                    "detail": p.detail,
                    "severity": p.severity,
                    "count": p.count,
                    "assets": p.assets[:4],
                }
                for p in self.paths[:8]
            ],
            "actions": [
                {
                    "title": a.title,
                    "severity": a.severity,
                    "effort": a.effort,
                    "clears": a.clears,
                    "assets": a.assets,
                }
                for a in self.actions[:10]
            ],
            "changes": [
                asdict(c)
                | {"added_sample": c.added_sample[:5], "gone_sample": c.gone_sample[:5]}
                for c in self.changes
            ],
            "concentration": [asdict(c) for c in self.concentration[:6]],
            "exposure": self.exposure,
            "hosting": self.hosting,
            "caveats": [c.text for c in self.caveats[:8]],
        }

    def prompt_json(self, *, limit: int = 14) -> str:
        body = json.dumps(
            self.prompt_payload(limit=limit), separators=(",", ":"), default=str
        )
        if len(body) <= MAX_BRIEF_BYTES:
            return body
        return json.dumps(
            self.prompt_payload(limit=6), separators=(",", ":"), default=str
        )[:MAX_BRIEF_BYTES]
