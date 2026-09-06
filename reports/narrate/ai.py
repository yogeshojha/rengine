"""The model writes from the brief and nothing else. A failure falls back to the plain narrator."""

from __future__ import annotations

from reports.analysis.brief import AttackPath, ReportBrief
from reports.data.models import Issue
from reports.narrate.base import Narrator
from reports.narrate.deterministic import PlainNarrator
from shared.definitions.ai import AITask
from shared.definitions.reports import Audience, Depth, NarrativeOptions
from shared.services.ai.cache import narrate
from shared.services.ai.config import AIConfig

_VOICE = (
    "You write security reports for a mature attack surface management product. "
    "Rules you must follow exactly:\n"
    "- Use only the facts in the JSON brief. Never invent a number, a hostname, a CVE or a date.\n"
    "- Plain declarative sentences, one idea each. No marketing language, no hedging, no filler.\n"
    "- Never use em dashes. Never use rhetorical questions. Never open with 'In today's landscape'.\n"
    "- Do not restate the brief as a list of counts. Say what the counts mean for this estate.\n"
    "- Refer to the subject by name. Write in the present tense about what the scan observed.\n"
    "- Output GitHub-flavoured Markdown. Never use headings above level 3. No code fences.\n"
    "- If a dimension was not scanned, say so rather than implying it is clean."
)

_AUDIENCE = {
    Audience.EXECUTIVE.value: (
        "Your reader owns the budget, not the servers. Lead with business consequence and "
        "the decision to make. Do not name tools, payloads or template identifiers."
    ),
    Audience.TECHNICAL.value: (
        "Your reader will fix this today. Be specific about assets, conditions and the order "
        "of work. Naming the weakness class is expected."
    ),
    Audience.MIXED.value: (
        "Your reader is a security lead who briefs executives and directs engineers. Open with "
        "consequence, then get specific."
    ),
}

_LENGTH = {
    Depth.BRIEF.value: "Write at most 120 words.",
    Depth.STANDARD.value: "Write 200 to 300 words in three or four short paragraphs.",
    Depth.DETAILED.value: "Write 400 to 550 words in five or six short paragraphs.",
}


class AiNarrator(Narrator):
    ai_used = True

    def __init__(self, session, cfg: AIConfig, options: NarrativeOptions) -> None:
        super().__init__()
        self.session = session
        self.cfg = cfg
        self.options = options
        self.fallback = PlainNarrator()
        self.used_model = False

    # ---------- prompt plumbing ----------

    def _system(self) -> str:
        audience = _AUDIENCE.get(self.options.audience, _AUDIENCE[Audience.MIXED.value])
        house = self.options.house_style.strip()
        extra = f"\nHouse style the client asked for: {house}" if house else ""
        return f"{_VOICE}\n\n{audience}{extra}"

    def _ask(
        self,
        task: str,
        instruction: str,
        payload: str,
        *,
        subject: str,
        fast: bool = False,
    ) -> str | None:
        prompt = f"{instruction}\n\nBRIEF:\n{payload}"
        text = narrate(
            self.session,
            self.cfg,
            task=task,
            system=self._system(),
            prompt=prompt,
            subject=subject,
            fast=fast,
            usage=self.usage,
        )
        if text:
            self.used_model = True
        return text

    # ---------- sections ----------

    def executive_summary(self, brief: ReportBrief) -> str:
        instruction = (
            "Write the executive summary of this report. "
            f"{_LENGTH.get(self.options.depth, _LENGTH[Depth.STANDARD.value])} "
            "Cover, in this order: what was assessed and what the run produced; the risk "
            "position and what drives it; the one or two chains that matter most; what "
            "changed since the previous run; and the single action to take first. "
            "Finish with one sentence naming what this report cannot speak to, taken from "
            "the caveats. Do not use bullet points."
        )
        return self._ask(
            AITask.EXECUTIVE_SUMMARY.value,
            instruction,
            brief.prompt_json(),
            subject=brief.subject,
        ) or self.fallback.executive_summary(brief)

    def risk_narrative(self, brief: ReportBrief) -> str:
        instruction = (
            "Explain why the top risks rank the way they do, and where risk is concentrated. "
            "Two short paragraphs at most. Use the signals given for each risk rather than "
            "restating severity. Do not use bullet points."
        )
        return self._ask(
            AITask.RISK_NARRATIVE.value,
            instruction,
            brief.prompt_json(limit=8),
            subject=brief.subject,
        ) or self.fallback.risk_narrative(brief)

    def remediation_plan(self, brief: ReportBrief) -> str:
        instruction = (
            "Write the opening of a remediation plan: two short paragraphs saying how the "
            "work should be sequenced for this estate and why that order removes the most "
            "risk soonest. Reference the actions by name. Do not number them, the table "
            "that follows does that."
        )
        return self._ask(
            AITask.REMEDIATION_PLAN.value,
            instruction,
            brief.prompt_json(limit=10),
            subject=brief.subject,
        ) or self.fallback.remediation_plan(brief)

    def surface_narrative(self, brief: ReportBrief) -> str:
        instruction = (
            "Describe how this attack surface is shaped and hosted, and what that shape "
            "means for defence. Two short paragraphs. Use only the hosting and exposure "
            "figures in the brief."
        )
        return self._ask(
            AITask.SURFACE_NARRATIVE.value,
            instruction,
            brief.prompt_json(limit=4),
            subject=brief.subject,
        ) or self.fallback.surface_narrative(brief)

    def attack_path(self, path: AttackPath) -> str:
        if not self.options.ai_enabled:
            return path.detail
        payload = (
            f'{{"title":"{path.title}","severity":"{path.severity}","count":{path.count},'
            f'"evidence":{path.evidence[:5]},"assets":{path.assets[:5]}}}'
        )
        instruction = (
            "Write two or three sentences describing how an attacker uses this condition, "
            "and what it leads to next. Be concrete. Do not repeat the title."
        )
        return (
            self._ask(
                AITask.ATTACK_PATH.value,
                instruction,
                payload,
                subject=path.key,
                fast=True,
            )
            or path.detail
        )

    def issue_explainer(self, issue: Issue) -> str | None:
        if not self.options.explain_findings:
            return None
        payload = (
            f'{{"check":"{issue.name}","severity":"{issue.severity}",'
            f'"tags":{issue.tags[:8]},"cwe":{issue.cwe_ids[:3]},"cve":{issue.cve_ids[:3]},'
            f'"observations":{issue.count},"hosts":{len(issue.hosts)}}}'
        )
        instruction = (
            "In at most 70 words, say what this weakness lets an attacker do and what a "
            "defender should verify first. Do not restate the check name or the severity."
        )
        return self._ask(
            AITask.ISSUE_EXPLAINER.value,
            instruction,
            payload,
            subject=issue.template_id,
            fast=True,
        )
