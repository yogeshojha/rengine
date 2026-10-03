from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

import pytest
from fastapi import HTTPException

from app.services import endpoint as endpoint_module
from app.services.endpoint import EndpointService
from app.services.program_coverage import scope_match
from app.services.scan_context import _validate_exclusion_patterns, _validate_paths
from shared.definitions.bounty_programs import ScopeState
from shared.definitions.watch import excluded_by, plan_scope
from shared.enums.target import TargetType
from shared.models.endpoint import VerifyBranchRequest
from shared.services import scope_filter
from shared.services.scope_filter import (
    BACKREFERENCE,
    MAX_TIMEOUTS,
    NESTED_REPEAT,
    REPEATED_ALTERNATION,
    TOO_DEEP,
    TOO_MANY_REPEATS,
    compile_pattern,
    host_excluded,
    ip_excluded,
    matches_any,
    pattern_hazard,
)

pytestmark = pytest.mark.api

EXPLOIT = "a" * 40 + "!"


@pytest.fixture(autouse=True)
def fresh_patterns():
    compile_pattern.cache_clear()
    yield
    compile_pattern.cache_clear()


@pytest.mark.parametrize(
    ("pattern", "reason"),
    [
        ("(a|a)+$", REPEATED_ALTERNATION),
        ("(a|aa)+$", REPEATED_ALTERNATION),
        (r"(\w|\d)+!", REPEATED_ALTERNATION),
        ("/(x|xx)*/", REPEATED_ALTERNATION),
        ("(a+)+$", NESTED_REPEAT),
        ("(a*)*b", NESTED_REPEAT),
        (r"(\.\w+){2,}", NESTED_REPEAT),
        (r"(a)\1", BACKREFERENCE),
        ("(?P<x>a)(?P=x)", BACKREFERENCE),
        ("x{99999999}", TOO_MANY_REPEATS),
        ("((a{100}){100}){100}", TOO_MANY_REPEATS),
        ("(" * 600 + "a" + ")" * 600, TOO_DEEP),
    ],
)
def test_backtracking_constructs_are_refused(pattern, reason):
    assert pattern_hazard(pattern) == reason


@pytest.mark.parametrize(
    "pattern",
    [
        "admin",
        "/admin",
        "/admin/*",
        "*admin*",
        "*(a|aa)*",
        "^/api/v[0-9]+/",
        r"(^|\.)example\.com$",
        "/(api|v1)/",
        "(foo|bar)?",
        r"^(\d{1,3}\.){3}\d{1,3}$",
        "[(]+",
        r"\w+\.\w+\.example\.com",
        "/[a-f0-9]{64}",
    ],
)
def test_ordinary_patterns_are_accepted(pattern):
    assert pattern_hazard(pattern) is None


def test_ordinary_patterns_still_match():
    assert matches_any("/x/Admin/y", ["*admin*"])
    assert matches_any("/ADMIN/users", ["^/admin"])
    assert matches_any("/v1/internal/x", ["internal"])
    assert not matches_any("/api/users", ["/admin", "*secret*"])
    assert not matches_any("/api/users", [])
    assert matches_any("dev.acme.com", [r"(^|\.)dev\.acme\.com$"])
    assert not matches_any("prod.acme.com", [r"(^|\.)dev\.acme\.com$"])
    assert ip_excluded("10.1.2.3", ["10.0.0.0/8"])
    assert not ip_excluded("11.1.2.3", ["10.0.0.0/8"])
    assert host_excluded("10.1.2.3", [], ["10.0.0.0/8"])
    assert not host_excluded("www.acme.com", ["*.internal"], ["10.0.0.0/8"])


@pytest.mark.parametrize("pattern", ["(a|aa)+$", "(a|a)+$"])
def test_the_exploit_is_bounded_and_excludes(pattern):
    started = time.perf_counter()
    assert matches_any(EXPLOIT, [pattern])
    assert ip_excluded(EXPLOIT, [pattern])
    assert host_excluded(EXPLOIT, [pattern], [])
    assert time.perf_counter() - started < 1


@pytest.mark.parametrize("pattern", ["(a+)+$", r"(\w|\d)+!", ".*.*.*.*.*x"])
def test_other_backtracking_shapes_are_bounded(pattern):
    started = time.perf_counter()
    matches_any(EXPLOIT * 50, [pattern])
    assert time.perf_counter() - started < 1


def test_a_pattern_that_keeps_timing_out_is_no_longer_run():
    started = time.perf_counter()
    assert all(matches_any(EXPLOIT, ["(a|aa)+$"]) for _ in range(40))
    assert compile_pattern("(a|aa)+$").timeouts == MAX_TIMEOUTS
    assert time.perf_counter() - started < MAX_TIMEOUTS * 0.5
    assert not matches_any("/login", ["(b|bb)+$"])


@pytest.mark.parametrize(
    "pattern", ["x{99999999}", "(?:ab){9999999}", "(" * 600 + "a" + ")" * 600]
)
def test_a_pattern_that_cannot_compile_safely_excludes(pattern):
    started = time.perf_counter()
    assert matches_any("/anything", [pattern])
    assert time.perf_counter() - started < 1


def test_a_timeout_is_not_read_as_no_match(monkeypatch):
    class Stalled:
        def search(self, *_args, **_kwargs):
            raise TimeoutError

    entry = scope_filter.Exclusion("/admin", Stalled())
    monkeypatch.setattr(scope_filter, "compile_pattern", lambda _p: entry)
    assert matches_any("/public", ["/admin"])


@pytest.mark.parametrize(
    "pattern", ["(a|aa)+$", "(a+)+$", r"(a)\1", "x{99999999}", "(" * 600 + ")" * 600]
)
def test_saving_a_backtracking_pattern_is_refused(pattern):
    with pytest.raises(HTTPException) as caught:
        _validate_exclusion_patterns("excluded_subdomains", [pattern])
    assert caught.value.status_code == 400
    assert pattern_hazard(pattern) in caught.value.detail
    with pytest.raises(HTTPException) as caught:
        _validate_paths([f"/{pattern}"])
    assert caught.value.status_code == 400


def test_saving_ordinary_patterns_is_accepted():
    _validate_paths(["/admin", "/admin/*", "/api/(v1|v2)/"])
    _validate_exclusion_patterns("excluded_subdomains", ["admin", "*staging*"])


@dataclass
class Scope:
    asset_identifier: str
    target_value: str
    scope_state: str = ScopeState.IN_SCOPE.value
    target_type: TargetType = TargetType.DOMAIN
    id: uuid.UUID = field(default_factory=uuid.uuid4)


def test_program_exclusions_stay_enforceable():
    scopes = [
        Scope("*.acme.com", "acme.com"),
        Scope("*.corp.acme.com", "corp.acme.com", ScopeState.OUT_OF_SCOPE.value),
        Scope("admin.acme.com", "admin.acme.com", ScopeState.OUT_OF_SCOPE.value),
    ]
    plan = plan_scope(scopes)
    assert len(plan.excluded_subdomains) == 2
    assert not plan.unenforceable
    assert excluded_by("vpn.corp.acme.com", plan.excluded_subdomains)
    assert not excluded_by("shop.acme.com", plan.excluded_subdomains)
    assert scope_match("admin.acme.com", scopes)[1]
    assert not scope_match("shop.acme.com", scopes)[1]


async def test_verify_branch_counts_a_timed_out_path_as_excluded(
    estate, session, now, monkeypatch
):
    sid = await estate.scan(
        "example.com", "run", at=now, config={"excluded_paths": ["(a|aa)+$"]}
    )
    await estate.endpoints("run", ["/login", "/api/users", f"/{EXPLOIT}"], at=now)
    monkeypatch.setattr(endpoint_module, "dispatch_endpoint_verify", lambda *_: True)
    started = time.perf_counter()
    result = await EndpointService(session).verify_branch(
        sid, VerifyBranchRequest(host="www.example.com")
    )
    assert time.perf_counter() - started < 1
    assert result.unverified == 2
    assert result.accepted
