from __future__ import annotations

import pytest

from shared.definitions.connectors import (
    ACTION_KIND_LABELS,
    CANDIDATE_STATE_LABELS,
    CONNECTOR_STATE_LABELS,
    INGESTED_TOOLS,
    LOUD_NOTICES,
    NOTICE_HELP,
    NOTICE_LABELS,
    SOURCE_TOOL_LABELS,
    ActionKind,
    CandidateState,
)
from tests.grammar.ts_mirror import Mirror

pytestmark = pytest.mark.grammar


@pytest.fixture(scope="module")
def mirror() -> Mirror:
    return Mirror("connectors.ts")


def test_the_frontend_mirror_carries_every_action(mirror: Mirror):
    assert mirror.values("ActionKind") == {a.value for a in ActionKind}
    assert mirror.labels("ACTION_KIND_LABELS") == ACTION_KIND_LABELS


def test_the_frontend_mirror_carries_the_state_and_tool_labels(mirror: Mirror):
    assert mirror.labels("CONNECTOR_STATE_LABELS") == CONNECTOR_STATE_LABELS
    assert mirror.labels("SOURCE_TOOL_LABELS") == SOURCE_TOOL_LABELS
    assert set(mirror.const("INGESTED_TOOLS")) == INGESTED_TOOLS


def test_the_frontend_mirror_carries_every_candidate_state(mirror: Mirror):
    assert mirror.const("CANDIDATE_STATES") == [s.value for s in CandidateState]
    assert mirror.labels("CANDIDATE_STATE_LABELS") == CANDIDATE_STATE_LABELS


def test_the_frontend_mirror_carries_every_notice(mirror: Mirror):
    assert mirror.labels("NOTICE_LABELS") == NOTICE_LABELS
    assert mirror.labels("NOTICE_HELP") == NOTICE_HELP
    assert mirror.const("LOUD_NOTICES") == LOUD_NOTICES
