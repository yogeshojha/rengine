from __future__ import annotations

import uuid
from dataclasses import dataclass, field

import pytest

from app.services.program_coverage import host_of, scope_match
from shared.definitions.bounty_programs import ScopeState
from shared.enums.target import TargetType

pytestmark = pytest.mark.api


@dataclass
class Scope:
    asset_identifier: str
    target_value: str
    scope_state: str = ScopeState.IN_SCOPE.value
    target_type: TargetType = TargetType.DOMAIN
    id: uuid.UUID = field(default_factory=uuid.uuid4)


def _scope(
    identifier: str, value: str, state: str = ScopeState.IN_SCOPE.value
) -> Scope:
    return Scope(asset_identifier=identifier, target_value=value, scope_state=state)


def test_a_wildcard_scope_covers_the_subtree():
    scopes = [_scope("*.acme.com", "acme.com")]
    assert scope_match("shop.acme.com", scopes)[0] is not None
    assert scope_match("acme.com", scopes)[0] is not None


def test_an_exact_scope_covers_only_itself():
    scopes = [_scope("www.acme.com", "www.acme.com")]
    assert scope_match("www.acme.com", scopes)[0] is not None
    assert scope_match("shop.acme.com", scopes)[0] is None


def test_a_suffix_is_not_a_subtree():
    scopes = [_scope("*.acme.com", "acme.com")]
    assert scope_match("notacme.com", scopes)[0] is None


def test_an_out_of_scope_entry_is_reported_as_excluded():
    scopes = [
        _scope("*.acme.com", "acme.com"),
        _scope("*.lab.acme.com", "lab.acme.com", ScopeState.OUT_OF_SCOPE.value),
    ]
    scope, excluded = scope_match("box.lab.acme.com", scopes)
    assert scope is not None
    assert excluded


def test_a_url_scope_is_read_as_its_host():
    assert host_of("https://shop.acme.com/login") == "shop.acme.com"
    assert host_of("*.acme.com") == "acme.com"
    assert host_of("acme.com:8443") == "acme.com"
