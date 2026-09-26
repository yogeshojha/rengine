from __future__ import annotations

import pytest

from shared.definitions.new_checks import TARGET_FLAG_HELP, TARGET_FLAG_TITLE
from tests.grammar.ts_mirror import Mirror

pytestmark = pytest.mark.grammar


def test_the_frontend_mirror_carries_the_flag_title_and_help():
    mirror = Mirror("new-checks.ts")
    assert mirror.const("NEW_CHECKS_TITLE") == TARGET_FLAG_TITLE
    assert mirror.const("NEW_CHECKS_HELP") == TARGET_FLAG_HELP
