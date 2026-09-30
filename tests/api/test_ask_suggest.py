"""Ask: the decision line at the end of an answer."""

from __future__ import annotations

import pytest

from app.services.ask import suggest
from shared.definitions.ask import Decision, NextStep

pytestmark = pytest.mark.api


def test_a_decision_line_is_parsed_and_removed():
    text, found = suggest.split(
        "The banner is static [F1].\n\n>> decision=false_positive next=none"
    )
    assert text == "The banner is static [F1]."
    assert found is not None
    assert found.decision == Decision.FALSE_POSITIVE.value
    assert found.next == NextStep.NONE.value


def test_unknown_values_fall_to_none_and_an_empty_line_is_dropped():
    text, found = suggest.split("Real.\n>> decision=confirmed next=notify")
    assert text == "Real."
    assert (found.decision, found.next) == (
        Decision.CONFIRMED.value,
        NextStep.NONE.value,
    )
    text, found = suggest.split("Hi.\n>> decision=none next=none")
    assert text == "Hi."
    assert found is None


def test_an_answer_without_the_line_is_untouched():
    text, found = suggest.split(
        "Hello. Ask about the finding's impact or reproduction."
    )
    assert text.startswith("Hello.")
    assert found is None
