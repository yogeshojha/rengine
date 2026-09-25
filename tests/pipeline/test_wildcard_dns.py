from __future__ import annotations

import pytest

from stages.subdomain.stage import (
    _WILDCARD_PROBES,
    SubdomainStage,
    _Resolution,
    _Wildcard,
)

pytestmark = pytest.mark.pipeline


def test_overlap_drops_a_partial_pool_answer() -> None:
    wildcard = _Wildcard(ips=frozenset({"1.1.1.1", "1.1.1.2", "1.1.1.3"}))
    # one shared pool address is a wildcard match
    assert wildcard.matches({"ips": ["1.1.1.3", "9.9.9.9"]})
    assert wildcard.matches({"ips": ["1.1.1.1"]})


def test_a_distinct_address_is_kept() -> None:
    wildcard = _Wildcard(ips=frozenset({"1.1.1.1", "1.1.1.2"}))
    assert not wildcard.matches({"ips": ["8.8.8.8"]})


def test_wildcard_cname_is_matched() -> None:
    wildcard = _Wildcard(cnames=frozenset({"pool.cdn.example."}))
    assert wildcard.matches({"cname": "pool.cdn.example."})
    assert not wildcard.matches({"cname": "real.origin.example."})


def test_an_empty_profile_matches_nothing() -> None:
    empty = _Wildcard()
    assert not empty
    assert not empty.matches({"ips": ["1.2.3.4"]})


def test_a_quorum_of_answers_unions_their_addresses() -> None:
    stage = SubdomainStage.__new__(SubdomainStage)
    pool = ["10.0.0.1", "10.0.0.2"]
    stage._resolve = lambda names: _Resolution(  # type: ignore[method-assign]
        records={n: {"ips": [pool[i % 2]], "active": True} for i, n in enumerate(names)}
    )
    result = stage._wildcard_profile("example.com")
    assert result.ips == frozenset(pool)


def test_below_the_quorum_is_not_a_wildcard_zone() -> None:
    stage = SubdomainStage.__new__(SubdomainStage)
    calls = {"n": 0}

    def resolve(names):
        # only two of five probes answer
        out = {}
        for name in names:
            calls["n"] += 1
            out[name] = {"ips": ["7.7.7.7"], "active": True} if calls["n"] <= 2 else {}
        return _Resolution(records=out)

    stage._resolve = resolve  # type: ignore[method-assign]
    assert not stage._wildcard_profile("example.com")


def test_sends_several_probes() -> None:
    stage = SubdomainStage.__new__(SubdomainStage)
    seen: list[int] = []
    stage._resolve = lambda names: seen.append(len(names)) or _Resolution()  # type: ignore[method-assign]
    stage._wildcard_profile("example.com")
    assert seen == [_WILDCARD_PROBES]
