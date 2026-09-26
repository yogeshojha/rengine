from __future__ import annotations

import pytest

from shared.definitions.interest import InterestKind
from tests.grammar.ts_mirror import Mirror

pytestmark = pytest.mark.grammar


@pytest.fixture(scope="module")
def mirror() -> Mirror:
    return Mirror("interest.ts")


def test_the_frontend_mirror_carries_every_kind(mirror: Mirror):
    assert mirror.values("InterestKind") == {k.value for k in InterestKind}


def test_every_kind_has_an_icon(mirror: Mirror):
    assert set(mirror.const("KIND_ICONS")) == {k.value for k in InterestKind}
