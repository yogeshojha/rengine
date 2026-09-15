"""The evidence ladder: how a finding or inference was established."""

from __future__ import annotations

from enum import StrEnum


class Evidence(StrEnum):
    INFERRED = "inferred"
    OBSERVED = "observed"
    CORROBORATED = "corroborated"
    PROVEN = "proven"


EVIDENCE_ORDER: tuple[str, ...] = tuple(e.value for e in Evidence)

EVIDENCE_RANK: dict[str, int] = {value: i for i, value in enumerate(EVIDENCE_ORDER)}

EVIDENCE_LABELS: dict[str, str] = {
    Evidence.INFERRED.value: "Inferred",
    Evidence.OBSERVED.value: "Observed",
    Evidence.CORROBORATED.value: "Corroborated",
    Evidence.PROVEN.value: "Proven",
}

EVIDENCE_HELP: dict[str, str] = {
    Evidence.INFERRED.value: "The reported version falls inside the affected range.",
    Evidence.OBSERVED.value: "A check matched the response it received.",
    Evidence.CORROBORATED.value: "Two independent signals agree at the same location.",
    Evidence.PROVEN.value: "The asset produced an out-of-band interaction.",
}


def evidence_rank(value: str | None) -> int:
    return EVIDENCE_RANK.get(value or "", -1)


def evidence_label(value: str | None) -> str:
    return EVIDENCE_LABELS.get(value or "", "")
