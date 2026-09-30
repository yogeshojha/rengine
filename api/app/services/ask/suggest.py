"""The decision line the model ends an answer with."""

from __future__ import annotations

from shared.definitions.ask import SUGGESTION, Decision, NextStep
from shared.models.ask import Suggestion

DECISIONS = frozenset(d.value for d in Decision)
NEXT_STEPS = frozenset(n.value for n in NextStep)


def split(text: str) -> tuple[str, Suggestion | None]:
    found = SUGGESTION.search(text)
    if found is None:
        return text, None
    decision, step = found.group(1).lower(), found.group(2).lower()
    suggestion = Suggestion(
        decision=decision if decision in DECISIONS else Decision.NONE.value,
        next=step if step in NEXT_STEPS else NextStep.NONE.value,
    )
    if (
        suggestion.decision == Decision.NONE.value
        and suggestion.next == NextStep.NONE.value
    ):
        return text[: found.start()].rstrip(), None
    return text[: found.start()].rstrip(), suggestion
