from __future__ import annotations

import pytest

from shared.definitions.bounty_programs import (
    PLATFORMS_BY_KEY,
    ProgramSource,
    ProgramState,
    ScopeState,
    SubmissionState,
)
from shared.enums.target import TargetType
from shared.services.bounty_providers import PROVIDERS_BY_PLATFORM
from shared.services.bounty_providers.intigriti import (
    IntigritiProvider,
    _program_row,
    _scope_row,
)

pytestmark = pytest.mark.api


def _enum(value_id: int, value: str) -> dict:
    return {"id": value_id, "value": value}


def _program(**over) -> dict:
    return {
        "id": "c1a89c7e-5de0-435d-a30f-a8c16e65ccfc",
        "handle": "adobepublic",
        "name": "Adobe Public",
        "following": False,
        "minBounty": {"value": 75, "currency": "USD"},
        "maxBounty": {"value": 15000, "currency": "USD"},
        "confidentialityLevel": _enum(4, "Public"),
        "status": _enum(3, "Open"),
        "type": _enum(1, "Bug bounty"),
        "webLinks": {"detail": "?redirect=/programs/adobe/adobepublic/detail"},
        "industry": "Software",
        **over,
    }


def _domain(**over) -> dict:
    return {
        "id": "1f0d3e1a-0000-4000-8000-000000000001",
        "type": _enum(7, "Wildcard"),
        "endpoint": "*.example.com",
        "tier": _enum(4, "Tier 1"),
        "description": "Everything under the apex",
        "requiredSkills": [],
        **over,
    }


def test_every_api_platform_has_a_provider():
    for spec in PLATFORMS_BY_KEY.values():
        if spec.api_provider:
            assert spec.key in PROVIDERS_BY_PLATFORM
            assert PROVIDERS_BY_PLATFORM[spec.key].api_provider.value == (
                spec.api_provider
            )
        else:
            assert spec.key not in PROVIDERS_BY_PLATFORM


def test_a_public_program_carries_its_payout_and_platform_id():
    row = _program_row(_program())
    assert row["external_id"] == "c1a89c7e-5de0-435d-a30f-a8c16e65ccfc"
    assert row["handle"] == "adobepublic"
    assert row["source"] == ProgramSource.API.value
    assert row["program_state"] == ProgramState.PUBLIC.value
    assert row["submission_state"] == SubmissionState.OPEN.value
    assert (
        row["url"]
        == "https://app.intigriti.com/researcher/programs/adobe/adobepublic/detail"
    )
    assert row["min_payout"] == 75
    assert row["max_payout"] == 15000
    assert row["payout_currency"] == "USD"
    assert row["offers_bounties"] is True


@pytest.mark.parametrize(
    ("level", "state"),
    [
        (4, ProgramState.PUBLIC.value),
        (3, ProgramState.PRIVATE.value),
        (2, ProgramState.PRIVATE.value),
        (1, ProgramState.PRIVATE.value),
    ],
)
def test_confidentiality_decides_whether_a_program_is_private(level, state):
    row = _program_row(_program(confidentialityLevel=_enum(level, "x")))
    assert row["program_state"] == state


def test_the_program_list_never_claims_membership():
    assert "joined" not in _program_row(_program())


@pytest.mark.parametrize(
    ("status_id", "expected"),
    [
        (3, SubmissionState.OPEN.value),
        (4, SubmissionState.PAUSED.value),
        (5, SubmissionState.CLOSED.value),
        (99, SubmissionState.UNKNOWN.value),
    ],
)
def test_status_maps_to_a_submission_state(status_id, expected):
    row = _program_row(_program(status=_enum(status_id, "x")))
    assert row["submission_state"] == expected


def test_a_vdp_program_does_not_claim_bounties():
    row = _program_row(_program(maxBounty={"value": 0, "currency": "EUR"}))
    assert row["offers_bounties"] is False
    assert row["max_payout"] == 0


def test_a_program_without_a_handle_or_id_is_dropped():
    assert _program_row(_program(handle="")) is None
    assert _program_row(_program(id="")) is None


def test_an_absolute_detail_link_is_kept_as_is():
    row = _program_row(
        _program(
            webLinks={"detail": "https://app.intigriti.com/researcher/programs/a/b"}
        )
    )
    assert row["url"] == "https://app.intigriti.com/researcher/programs/a/b"


def test_a_wildcard_becomes_an_importable_domain_target():
    row = _scope_row(_domain())
    assert row["asset_type"] == "WILDCARD"
    assert row["scope_state"] == ScopeState.IN_SCOPE.value
    assert row["tier"] == "Tier 1"
    assert row["eligible_for_bounty"] is True
    assert row["target_value"] == "example.com"
    assert row["target_type"] is TargetType.DOMAIN


@pytest.mark.parametrize(
    ("type_id", "asset_type"),
    [
        (1, "URL"),
        (2, "GOOGLE_PLAY_APP_ID"),
        (3, "APPLE_STORE_APP_ID"),
        (4, "CIDR"),
        (5, "HARDWARE"),
        (6, "OTHER"),
        (7, "WILDCARD"),
        (8, "SOURCE_CODE"),
        (99, "OTHER"),
    ],
)
def test_every_domain_type_maps_to_an_asset_type(type_id, asset_type):
    row = _scope_row(_domain(type=_enum(type_id, "x"), endpoint="thing"))
    assert row["asset_type"] == asset_type


def test_the_out_of_scope_tier_is_a_state_not_a_band():
    row = _scope_row(_domain(tier=_enum(5, "Out Of Scope")))
    assert row["scope_state"] == ScopeState.OUT_OF_SCOPE.value
    assert row["tier"] is None
    assert row["eligible_for_bounty"] is None


def test_the_no_bounty_tier_stays_in_scope_and_pays_nothing():
    row = _scope_row(_domain(tier=_enum(1, "No Bounty")))
    assert row["scope_state"] == ScopeState.IN_SCOPE.value
    assert row["tier"] == "No Bounty"
    assert row["eligible_for_bounty"] is False


@pytest.mark.parametrize(
    ("tier_id", "label", "band", "eligible"),
    [
        (1, "No Bounty", "No Bounty", False),
        (2, "Tier 3", "Tier 3", True),
        (3, "Tier 2", "Tier 2", True),
        (4, "Tier 1", "Tier 1", True),
        (6, "Tier 4", "Tier 4", True),
        (7, "Tier 5", "Tier 5", True),
    ],
)
def test_every_paying_tier_stays_in_scope(tier_id, label, band, eligible):
    row = _scope_row(_domain(tier=_enum(tier_id, label)))
    assert row["scope_state"] == ScopeState.IN_SCOPE.value
    assert row["tier"] == band
    assert row["eligible_for_bounty"] is eligible


def test_the_out_of_scope_label_wins_without_its_id():
    row = _scope_row(_domain(tier=_enum(99, "Out Of Scope")))
    assert row["scope_state"] == ScopeState.OUT_OF_SCOPE.value


def test_an_empty_endpoint_is_dropped():
    assert _scope_row(_domain(endpoint="   ")) is None


def test_an_unreachable_asset_still_records_its_scope():
    row = _scope_row(
        _domain(
            type=_enum(3, "iOS"), endpoint="com.example.app", tier=_enum(2, "Tier 2")
        )
    )
    assert row["asset_type"] == "APPLE_STORE_APP_ID"
    assert row["target_value"] is None
    assert row["tier"] == "Tier 2"


def test_paging_follows_max_count(monkeypatch):
    provider = IntigritiProvider("token")
    pages = [
        {
            "maxCount": 3,
            "records": [_program(id=f"id-{i}", handle=f"p{i}") for i in range(2)],
        },
        {"maxCount": 3, "records": [_program(id="id-2", handle="p2")]},
    ]
    calls: list[dict] = []

    def fake_get(url, params=None):
        calls.append(params or {})
        return pages[len(calls) - 1]

    monkeypatch.setattr(provider.client, "get", fake_get)
    rows = provider.programs()
    assert [r["handle"] for r in rows] == ["p0", "p1", "p2"]
    assert [c["offset"] for c in calls] == [0, 2]


def test_paging_stops_on_an_empty_page(monkeypatch):
    provider = IntigritiProvider("token")
    monkeypatch.setattr(
        provider.client, "get", lambda *_a, **_k: {"maxCount": 99, "records": []}
    )
    assert provider.programs() == []


def test_scope_reads_the_current_domain_version(monkeypatch):
    provider = IntigritiProvider("token")
    program = type(
        "P",
        (),
        {
            "external_id": "abc",
            "handle": "p",
            "id": "local",
            "program_state": ProgramState.PUBLIC.value,
        },
    )()
    monkeypatch.setattr(
        provider.client,
        "get",
        lambda *_a, **_k: {
            "domains": {"id": "v1", "createdAt": 1757000000, "content": [_domain()]}
        },
    )
    fetched = provider.scopes(program)
    assert len(fetched.entries) == 1
    assert fetched.entries[0]["asset_identifier"] == "*.example.com"
    assert fetched.program_updates == {"joined": False}


@pytest.mark.parametrize(
    ("state", "joined"),
    [(ProgramState.PRIVATE.value, True), (ProgramState.PUBLIC.value, False)],
)
def test_reading_a_private_program_scope_proves_membership(monkeypatch, state, joined):
    provider = IntigritiProvider("token")
    program = type(
        "P", (), {"external_id": "abc", "handle": "p", "program_state": state}
    )()
    monkeypatch.setattr(
        provider.client, "get", lambda *_a, **_k: {"domains": {"content": []}}
    )
    assert provider.scopes(program).program_updates == {"joined": joined}
