"""Two narrators write the same sections from the same brief."""

from __future__ import annotations

from abc import ABC, abstractmethod

from reports.analysis.brief import AttackPath, ReportBrief
from reports.data.models import Issue
from shared.services.ai.client import AIUsage


class Narrator(ABC):
    ai_used: bool = False

    def __init__(self) -> None:
        self.usage = AIUsage()

    @abstractmethod
    def executive_summary(self, brief: ReportBrief) -> str: ...

    @abstractmethod
    def risk_narrative(self, brief: ReportBrief) -> str: ...

    @abstractmethod
    def remediation_plan(self, brief: ReportBrief) -> str: ...

    @abstractmethod
    def surface_narrative(self, brief: ReportBrief) -> str: ...

    def attack_path(self, path: AttackPath) -> str:
        return path.detail

    def issue_explainer(self, issue: Issue) -> str | None:
        del issue
        return None
