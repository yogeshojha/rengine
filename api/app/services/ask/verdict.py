"""What the stored rows say about a finding, before anyone asks."""

from __future__ import annotations

from collections.abc import Iterable

from shared.definitions.ask import (
    MAX_CITED_LINES,
    MAX_FACT_DETAIL,
    SECRET_TAGS,
    EvidenceField,
    FactTone,
    Verdict,
)
from shared.definitions.evidence import Evidence
from shared.definitions.vulnerabilities import VulnState
from shared.models.ask import Fact
from shared.models.software import SoftwareCve
from shared.models.vulnerability import VulnerabilityRead
from shared.services.issue_tracking.body import mask_secrets
from shared.utils.text import counted

BLOCKED_STATUSES = frozenset({401, 403, 429})
EVIDENCE_TONES = frozenset({FactTone.FOR.value})


def lines_with(text: str | None, needles: Iterable[str]) -> list[int]:
    """1-based lines of `text` holding any of the needles."""
    wanted = [n for n in needles if n]
    if not text or not wanted:
        return []
    found: list[int] = []
    for number, line in enumerate(text.split("\n"), 1):
        if any(n in line for n in wanted):
            found.append(number)
            if len(found) >= MAX_CITED_LINES:
                break
    return found


def hides_extracted(v: VulnerabilityRead) -> bool:
    words = {t.lower() for t in v.tags} | set(v.template_id.lower().split("-"))
    return bool(words & SECRET_TAGS)


def _clip(text: str | None) -> str | None:
    if not text:
        return None
    text = " ".join(text.split())
    return text if len(text) <= MAX_FACT_DETAIL else f"{text[: MAX_FACT_DETAIL - 1]}…"


def assess(
    v: VulnerabilityRead, *, software: SoftwareCve | None = None
) -> tuple[str, list[Fact]]:
    facts: list[Fact] = []

    def add(
        tone: FactTone,
        label: str,
        *,
        detail: str | None = None,
        field: str | None = None,
        lines: Iterable[int] = (),
    ) -> None:
        facts.append(
            Fact(
                n=len(facts) + 1,
                tone=tone.value,
                label=label,
                detail=_clip(detail),
                field=field,
                lines=list(lines),
            )
        )

    if v.evidence == Evidence.PROVEN.value:
        add(
            FactTone.FOR,
            "Callback received",
            detail="The target reached the out-of-band server.",
        )
    if v.matcher_name:
        add(FactTone.FOR, f"Matcher {v.matcher_name} matched")
    if v.extracted_results:
        add(
            FactTone.FOR,
            f"{counted(len(v.extracted_results), 'value')} extracted",
            detail=None
            if hides_extracted(v)
            else mask_secrets(", ".join(v.extracted_results[:3])),
            field=EvidenceField.RESPONSE.value if v.response else None,
            lines=lines_with(v.response, v.extracted_results),
        )
    if v.corroborated_by:
        add(
            FactTone.FOR,
            f"Corroborated by {counted(len(v.corroborated_by), 'check')}",
            detail=", ".join(c.template_name for c in v.corroborated_by[:3]),
        )
    if v.replays:
        add(FactTone.FOR, f"Reproduced on {counted(v.replays, 'equivalent web asset')}")
    if software is not None:
        add(
            FactTone.FOR,
            f"{software.product} {software.version} in the affected range",
            detail=f"Fixed in {software.fixed_in}" if software.fixed_in else None,
        )
    if v.state == VulnState.CONFIRMED.value:
        add(FactTone.FOR, "Confirmed in triage", detail=mask_secrets(v.note or ""))

    asset = v.asset
    if asset and asset.waf:
        add(
            FactTone.AGAINST,
            f"{asset.waf} in front",
            detail="A WAF page can satisfy a loose matcher.",
        )
    if asset and asset.status_code in BLOCKED_STATUSES:
        add(FactTone.AGAINST, f"Web asset answers {asset.status_code}")
    if v.state == VulnState.FALSE_POSITIVE.value:
        add(
            FactTone.AGAINST,
            "Marked false positive in triage",
            detail=mask_secrets(v.note or ""),
        )

    if not v.response:
        add(FactTone.UNKNOWN, "Response not stored")
    if not v.interaction and v.evidence != Evidence.PROVEN.value and "oast" in v.tags:
        add(FactTone.UNKNOWN, "No callback recorded")

    return _verdict(v, facts), facts


def _verdict(v: VulnerabilityRead, facts: list[Fact]) -> str:
    if v.state == VulnState.FALSE_POSITIVE.value:
        return Verdict.FALSE_POSITIVE.value
    if v.evidence == Evidence.PROVEN.value:
        return Verdict.PROVEN.value
    tones = {f.tone for f in facts}
    if FactTone.AGAINST.value in tones:
        return Verdict.UNCERTAIN.value
    if tones & EVIDENCE_TONES:
        return Verdict.LIKELY.value
    return Verdict.INSUFFICIENT.value
