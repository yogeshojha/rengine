from __future__ import annotations

import pytest

from shared.definitions.bounty_programs import BountyEvent
from shared.models.bounty_program import BountyProgram
from shared.services.bounty_programs import scope_changes, terms_changes

pytestmark = pytest.mark.api

KEY = ("DOMAIN", "app.acme.com")


def _program(**fields) -> BountyProgram:
    base = {
        "platform": "intigriti",
        "source": "feed",
        "handle": "acme",
        "name": "Acme",
        "program_state": "public",
        "submission_state": "open",
    }
    return BountyProgram(**{**base, **fields})


def _asset(**fields) -> dict:
    return {
        "scope_state": "in_scope",
        "tier": None,
        "eligible_for_bounty": None,
        "max_severity": None,
        "instruction": None,
        **fields,
    }


def test_a_payout_range_change_is_one_event():
    program = _program(min_payout=500, max_payout=5000, payout_currency="EUR")
    row = {"source": "feed", "min_payout": 1000, "max_payout": 10000}

    assert terms_changes(program, row) == [
        (BountyEvent.PAYOUT_CHANGED.value, "EUR 500 to 5,000 → EUR 1,000 to 10,000")
    ]


def test_a_payout_first_reported_is_not_a_change():
    program = _program(min_payout=None, max_payout=None)
    row = {"source": "feed", "min_payout": 100, "max_payout": 1000}

    assert terms_changes(program, row) == []


def test_safe_harbor_and_2fa_changes_are_one_rules_event():
    program = _program(safe_harbor="partial", requires_2fa=False)
    row = {"source": "feed", "safe_harbor": "full", "requires_2fa": True}

    assert terms_changes(program, row) == [
        (BountyEvent.RULES_CHANGED.value, "Safe harbor partial → full · 2FA required")
    ]


def test_a_source_switch_reports_no_terms():
    program = _program(min_payout=500, max_payout=5000, safe_harbor="full")
    row = {"source": "api", "min_payout": None, "max_payout": 100, "safe_harbor": None}

    assert terms_changes(program, row) == []


def test_an_asset_tier_change_is_a_bounty_event():
    program = _program()
    events = scope_changes(
        program, {KEY: _asset(tier="Tier 2")}, {KEY: _asset(tier="Tier 1")}
    )

    assert [(e.kind, e.asset_identifier, e.detail) for e in events] == [
        (BountyEvent.ASSET_BOUNTY_CHANGED.value, "app.acme.com", "Tier 2 → Tier 1")
    ]


def test_rewritten_instructions_are_a_rules_event():
    program = _program()
    events = scope_changes(
        program,
        {KEY: _asset(instruction="No automated scanning")},
        {KEY: _asset(instruction="Automated scanning up to 5 req/s")},
    )

    assert [(e.kind, e.detail) for e in events] == [
        (BountyEvent.ASSET_RULES_CHANGED.value, "Automated scanning up to 5 req/s")
    ]


def test_an_unchanged_asset_reports_nothing():
    program = _program()
    same = _asset(tier="Tier 1", instruction="Be nice")

    assert scope_changes(program, {KEY: same}, {KEY: dict(same)}) == []
