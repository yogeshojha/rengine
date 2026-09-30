"""Turn [F1], [T2] and [R12] references into numbered [[n]] citations."""

from __future__ import annotations

import re

from shared.definitions.ask import CITATION, CitationKind, EvidenceField, TraceStatus
from shared.models.ask import Citation, Fact, TraceStep


def resolve(
    text: str,
    facts: list[Fact],
    steps: list[TraceStep],
    *,
    response_lines: int = 0,
) -> tuple[str, list[Citation]]:
    done = [s for s in steps if s.status == TraceStatus.DONE.value]
    numbered: dict[str, int] = {}
    citations: list[Citation] = []

    def source(kind: str, index: int) -> Citation | None:
        if kind == "F" and 0 < index <= len(facts):
            f = facts[index - 1]
            return Citation(
                n=0,
                kind=CitationKind.FACT.value,
                label=f.label,
                detail=f.detail,
                field=f.field,
                lines=f.lines,
            )
        if kind == "T" and 0 < index <= len(done):
            s = done[index - 1]
            label = s.label if s.rows is None else f"{s.label} · {s.rows} rows"
            return Citation(
                n=0, kind=CitationKind.TOOL.value, label=label, pivot=s.pivot
            )
        if kind == "R" and 0 < index <= response_lines:
            return Citation(
                n=0,
                kind=CitationKind.LINE.value,
                label=f"Response line {index}",
                field=EvidenceField.RESPONSE.value,
                lines=[index],
            )
        return None

    def replace(match: re.Match) -> str:
        space, kind, index = match.group(1), match.group(2), int(match.group(3))
        key = f"{kind}{index}"
        if key not in numbered:
            cite = source(kind, index)
            if cite is None:
                return ""
            cite.n = len(citations) + 1
            numbered[key] = cite.n
            citations.append(cite)
        return f"{space}[[{numbered[key]}]]"

    return CITATION.sub(replace, text).strip(), citations
