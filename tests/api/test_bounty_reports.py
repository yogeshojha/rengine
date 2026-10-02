from __future__ import annotations

import pytest

from app.api.deps import get_current_superuser
from app.api.v1.bounty_reports import router
from shared.definitions.bounty_programs import PLATFORMS
from shared.definitions.bounty_reports import SETTLED_STATES, ReportStage, report_state
from shared.services.bounty_providers import PROVIDERS_BY_PLATFORM, BountyProvider
from shared.services.bounty_providers.hackerone import (
    _account,
    _award_row,
    _report_row,
)

pytestmark = pytest.mark.api


def _rel(kind: str, ident: str, **attrs) -> dict:
    return {"data": {"id": ident, "type": kind, "attributes": attrs}}


def _report(**over) -> dict:
    return {
        "id": "774663",
        "type": "report",
        "attributes": {
            "title": "Authentication bypass via OTP bruteforce",
            "state": "resolved",
            "submitted_at": "2020-01-14T11:57:25.379Z",
            "closed_at": "2020-01-20T10:00:00.000Z",
            "last_activity_at": None,
            "last_program_activity_at": "2020-01-20T10:00:00.000Z",
            "bounty_awarded_at": "2020-01-25T02:20:22.715Z",
            **over,
        },
        "relationships": {
            "program": _rel("program", "1", handle="affirm"),
            "severity": _rel("severity", "2", rating="high", score=8.1),
            "weakness": _rel("weakness", "3", name="Improper Authentication"),
            "structured_scope": _rel(
                "structured-scope", "4", asset_type="URL", asset_identifier="x.test"
            ),
            "reporter": _rel(
                "user", "5", username="h", reputation=643, signal=5.8, impact=20.6
            ),
        },
    }


def _earning(**bounty) -> dict:
    return {
        "id": "e1",
        "type": "earning-bounty-earned",
        "attributes": {"amount": 150.0, "created_at": "2020-01-25T02:20:22.715Z"},
        "relationships": {
            "program": _rel(
                "program", "1", handle="affirm", name="Affirm", currency=None
            ),
            "bounty": {
                "data": {
                    "id": "b1",
                    "type": "bounty",
                    "attributes": {
                        "awarded_amount": "150.00",
                        "awarded_bonus_amount": "25.00",
                        "awarded_currency": "USD",
                        "created_at": "2020-01-25T02:20:22.715Z",
                        **bounty,
                    },
                    "relationships": {"report": {"data": {"id": "774663"}}},
                }
            },
        },
    }


def test_every_platform_that_tracks_reports_has_a_reader():
    for spec in PLATFORMS:
        if not spec.tracks_reports:
            continue
        cls = PROVIDERS_BY_PLATFORM[spec.key]
        assert cls.own_reports is not BountyProvider.own_reports
        assert "{id}" in spec.report_url


def test_a_report_row_reads_program_severity_and_scope():
    row = _report_row(_report())
    assert row["external_id"] == "774663"
    assert row["program_handle"] == "affirm"
    assert row["severity"] == "high"
    assert row["severity_score"] == 8.1
    assert row["weakness"] == "Improper Authentication"
    assert row["asset_identifier"] == "x.test"
    assert row["closed_at"] is not None


def test_an_unknown_severity_is_not_stored():
    entry = _report()
    entry["relationships"]["severity"] = _rel("severity", "2", rating="p1")
    assert _report_row(entry)["severity"] is None


def test_an_award_carries_amount_bonus_and_its_report():
    row = _award_row(_earning())
    assert row["amount"] == 150.0
    assert row["bonus"] == 25.0
    assert row["currency"] == "USD"
    assert row["report_external_id"] == "774663"
    assert row["program_name"] == "Affirm"


def test_an_award_without_a_bounty_currency_falls_back_to_the_platform():
    row = _award_row(_earning(awarded_currency=None))
    assert row["currency"] == "USD"


def test_an_award_without_an_amount_is_dropped():
    entry = _earning(awarded_amount=None)
    entry["attributes"]["amount"] = None
    assert _award_row(entry) is None


def test_the_account_is_read_off_the_reporter():
    assert _account([_report()]) == {
        "username": "h",
        "reputation": 643,
        "signal": 5.8,
        "impact": 20.6,
    }


@pytest.mark.parametrize(
    ("raw", "stage"),
    [
        ("triaged", ReportStage.OPEN),
        ("resolved", ReportStage.RESOLVED),
        ("duplicate", ReportStage.CLOSED),
        ("not-applicable", ReportStage.CLOSED),
        ("something-new", ReportStage.OPEN),
    ],
)
def test_every_state_has_a_stage(raw, stage):
    assert report_state(raw).stage is stage


def test_the_open_filter_matches_what_the_badge_calls_open():
    for raw in ("triaged", "pre-submission", ""):
        assert (report_state(raw).stage is ReportStage.OPEN) == (
            raw not in SETTLED_STATES
        )


def test_report_sync_is_superuser_only():
    route = next(
        r for r in router.routes if r.path == "/bounty-reports/{platform}/sync"
    )
    assert get_current_superuser in {d.call for d in route.dependant.dependencies}
