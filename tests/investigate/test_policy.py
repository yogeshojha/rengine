"""The policy that decides whether a proposed plan may run automatically."""

from __future__ import annotations

import pytest

from app.services.investigate.policy import (
    CREDENTIAL_TAGS,
    PlanInput,
    plan_cost,
    refuses,
)
from shared.definitions.investigate import (
    MAX_PLAN_REQUESTS,
    RefusalReason,
    Verdict,
    is_verified,
    tag_refusal,
    verdict_label,
)

pytestmark = pytest.mark.investigate


def _plan(**over) -> PlanInput:
    base = {
        "tags": frozenset({"cve"}),
        "needs_callback": False,
        "oast_ready": False,
        "request_count": 1,
        "in_scope": True,
        "budget_remaining": 40,
    }
    base.update(over)
    return PlanInput(**base)


def test_a_plain_in_scope_check_is_allowed():
    assert refuses(_plan()) is None


def test_out_of_scope_is_refused_before_anything_else():
    # an intrusive tag on an out-of-scope host still reports out of scope first
    assert refuses(_plan(in_scope=False, tags=frozenset({"intrusive"}))) == (
        RefusalReason.OUT_OF_SCOPE
    )


@pytest.mark.parametrize(
    ("tag", "reason"),
    [
        ("intrusive", RefusalReason.INTRUSIVE),
        ("dos", RefusalReason.DOS),
        ("fuzz", RefusalReason.FUZZ),
        ("fuzzing", RefusalReason.FUZZ),
    ],
)
def test_offensive_tags_are_refused(tag, reason):
    assert refuses(_plan(tags=frozenset({tag}))) == reason
    assert tag_refusal(frozenset({tag})) == reason


def test_tag_match_is_case_insensitive():
    assert refuses(_plan(tags=frozenset({"Intrusive"}))) == RefusalReason.INTRUSIVE


@pytest.mark.parametrize("tag", sorted(CREDENTIAL_TAGS))
def test_credential_checks_are_refused(tag):
    assert refuses(_plan(tags=frozenset({tag}))) == RefusalReason.CREDENTIALS


def test_a_callback_check_is_refused_without_a_listener():
    assert refuses(_plan(needs_callback=True, oast_ready=False)) == (
        RefusalReason.CALLBACK
    )


def test_a_callback_check_runs_when_a_listener_is_configured():
    assert refuses(_plan(needs_callback=True, oast_ready=True)) is None


def test_too_many_requests_is_refused():
    assert refuses(_plan(request_count=MAX_PLAN_REQUESTS + 1)) == RefusalReason.REQUESTS
    assert refuses(_plan(request_count=MAX_PLAN_REQUESTS)) is None


def test_the_budget_bounds_the_plan():
    assert refuses(_plan(request_count=5, budget_remaining=4)) == RefusalReason.BUDGET
    assert refuses(_plan(request_count=5, budget_remaining=5)) is None


def test_an_unknown_request_count_costs_one():
    assert plan_cost(None) == 1
    assert plan_cost(0) == 1
    assert plan_cost(7) == 7
    # a None count still clears a budget of one
    assert refuses(_plan(request_count=None, budget_remaining=1)) is None
    assert (
        refuses(_plan(request_count=None, budget_remaining=0)) == RefusalReason.BUDGET
    )


def test_an_offensive_tag_outranks_the_budget():
    # the reason reported is the tag, not the spent budget
    assert (
        refuses(
            _plan(tags=frozenset({"intrusive"}), request_count=99, budget_remaining=0)
        )
        == RefusalReason.INTRUSIVE
    )


def test_verified_verdicts():
    assert is_verified(Verdict.REPRODUCED.value)
    assert is_verified(Verdict.CONFIRMED.value)
    assert not is_verified(Verdict.NOT_REPRODUCED.value)
    assert not is_verified(Verdict.NEEDS_PERSON.value)
    assert not is_verified(Verdict.PENDING.value)


def test_verdict_label_falls_back_to_open():
    assert verdict_label("reproduced") == "Reproduced"
    assert verdict_label(None) == "Open"
    assert verdict_label("nonsense") == "Open"
