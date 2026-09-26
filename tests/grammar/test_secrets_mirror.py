from __future__ import annotations

import pytest

from shared.definitions.interest import TONE_INFO, TONE_NEUTRAL, TONE_WARNING
from shared.definitions.secrets import (
    DROP_REASON_LABELS,
    GROUP_LABELS,
    GROUP_ORDER,
    SOURCE_LABELS,
    STATE_LABELS,
    STATE_ORDER,
    STATE_TONES,
    DropReason,
    SecretGroup,
    SecretSource,
    SecretState,
)
from tests.grammar.ts_mirror import Mirror

pytestmark = pytest.mark.grammar

# the badge variant each backend tone renders as
TONE_BADGE = {TONE_WARNING: "warning", TONE_NEUTRAL: "outline", TONE_INFO: "info"}


@pytest.fixture(scope="module")
def mirror() -> Mirror:
    return Mirror("secrets.ts")


def test_the_frontend_mirror_carries_every_state(mirror: Mirror):
    assert mirror.values("SecretState") == {s.value for s in SecretState}
    assert tuple(mirror.const("STATE_ORDER")) == STATE_ORDER
    assert mirror.labels("STATE_LABELS") == STATE_LABELS
    assert mirror.labels("STATE_BADGE") == {
        state: TONE_BADGE[tone] for state, tone in STATE_TONES.items()
    }


def test_the_frontend_mirror_carries_every_group(mirror: Mirror):
    assert mirror.values("SecretGroup") == {g.value for g in SecretGroup}
    assert tuple(mirror.const("GROUP_ORDER")) == GROUP_ORDER
    assert mirror.labels("GROUP_LABELS") == GROUP_LABELS


def test_the_frontend_mirror_carries_every_source_and_drop_reason(mirror: Mirror):
    assert mirror.values("SecretSource") == {s.value for s in SecretSource}
    assert mirror.labels("SOURCE_LABELS") == SOURCE_LABELS
    assert set(DROP_REASON_LABELS) == {r.value for r in DropReason}
    assert mirror.labels("DROP_REASON_LABELS") == DROP_REASON_LABELS
