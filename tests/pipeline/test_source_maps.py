from __future__ import annotations

import json

import pytest

from shared.definitions.endpoints import EndpointSource
from stages.url_discovery.providers import URL_PROVIDERS, mine, response_mining
from stages.url_discovery.providers.katana import _detail
from stages.url_discovery.providers.source_maps import (
    SourceMapProvider,
    _Outcome,
    _State,
    _strip,
)

pytestmark = pytest.mark.pipeline

BUNDLE = "https://app.example.com/static/js/main.abc123.js"


def _map(sources: list[str], contents: list[str] | None = None) -> bytes:
    body: dict = {"version": 3, "sources": sources, "mappings": ""}
    if contents is not None:
        body["sourcesContent"] = contents
    return json.dumps(body).encode()


def _read(raw: bytes) -> _Outcome:
    outcome = _Outcome(bundle=BUNDLE, url=f"{BUNDLE}.map")
    outcome.read(raw)
    return outcome


def _in_scope(url: str) -> bool:
    return "example.com" in url


def test_a_real_map_is_recognised():
    outcome = _read(_map(["webpack:///./src/api/client.ts"]))
    assert outcome.exposed
    assert outcome.sources == ["webpack:///./src/api/client.ts"]


@pytest.mark.parametrize(
    "raw",
    [
        b"not json at all",
        b"<!doctype html><title>404</title>",
        json.dumps({"version": 3}).encode(),
        json.dumps({"version": 3, "sources": []}).encode(),
        json.dumps(["sources"]).encode(),
        b"",
    ],
)
def test_anything_that_is_not_a_map_is_not_one(raw: bytes):
    assert not _read(raw).exposed


def test_a_map_without_its_content_is_still_a_map():
    outcome = _read(_map(["webpack:///./src/app.ts"]))
    assert outcome.exposed
    assert outcome.contents == []


def _absorb(*outcomes: _Outcome) -> _State:
    state = _State()
    for outcome in outcomes:
        state.absorb(outcome, _in_scope)
    return state


def test_the_map_itself_is_an_endpoint():
    state = _absorb(_read(_map(["webpack:///./src/app.ts"])))
    assert [o.url for o in state.observations] == [f"{BUNDLE}.map"]
    assert "1 modules" in state.observations[0].detail


def test_urls_are_mined_out_of_the_original_source():
    contents = ['const api = "/api/v2/internal/users";\nfetch(api);']
    state = _absorb(_read(_map(["webpack:///./src/api.ts"], contents)))
    urls = {o.url for o in state.observations}
    assert "https://app.example.com/api/v2/internal/users" in urls


def test_an_out_of_scope_url_in_the_source_is_not_stored():
    contents = ['fetch("https://telemetry.vendor.io/collect");']
    state = _absorb(_read(_map(["webpack:///./src/api.ts"], contents)))
    assert all("vendor.io" not in o.url for o in state.observations)
    assert state.offsite == 1


def test_one_vendor_map_served_by_many_hosts_is_mined_once():
    raw = _map(["webpack:///./lib.ts"], ['fetch("/api/shared");'])
    first, second = _read(raw), _read(raw)
    second.bundle = "https://other.example.com/static/js/main.abc123.js"
    second.url = f"{second.bundle}.map"
    state = _absorb(first, second)

    assert state.exposed == 2, "both maps are reported"
    mined = [o for o in state.observations if o.url.endswith("/api/shared")]
    assert len(mined) == 1, "its source is read once"


def test_a_failure_is_counted_not_swallowed():
    outcome = _Outcome(bundle=BUNDLE, url=f"{BUNDLE}.map")
    outcome.failed = True
    assert _absorb(outcome).errors == 1


def test_a_map_too_large_to_read_is_said_so_rather_than_parsed_in_half():
    outcome = _Outcome(bundle=BUNDLE, url=f"{BUNDLE}.map")
    outcome.too_large = True
    state = _absorb(outcome)
    assert state.exposed == 0
    assert "too large" in state.note(asked=1)


def test_the_note_never_claims_a_map_that_was_not_there():
    assert "no source map" in _State().note(asked=40)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (f"{BUNDLE}?v=1", BUNDLE),
        (f"{BUNDLE}#x", BUNDLE),
        (BUNDLE, BUNDLE),
        ("https://a.example.com/x.js?1788345473=", "https://a.example.com/x.js"),
    ],
)
def test_the_query_string_is_not_part_of_the_file(url: str, expected: str):
    assert _strip(url) == expected


@pytest.mark.parametrize("url", ["ftp://example.com/x.js", "not a url", ""])
def test_anything_that_is_not_an_http_url_is_refused(url: str):
    assert _strip(url) is None


def test_it_is_a_registered_source_that_sends_requests():
    assert URL_PROVIDERS[EndpointSource.JS.value] is SourceMapProvider
    assert SourceMapProvider.touches_target is True, "a passive scan must skip it"
    assert SourceMapProvider.uses_session is True, "it reads the scan's own bundles"


def test_the_mining_vocabulary_is_shared_with_response_mining():
    assert response_mining.mine is mine


def test_a_url_read_out_of_a_bundle_does_not_claim_to_be_linked():
    detail = _detail({"found_on": "https://a.example.com/static/main.js", "tag": None})
    assert "javascript bundle" in detail
    assert "following links" not in detail


def test_a_url_that_was_linked_still_says_so():
    detail = _detail({"found_on": "https://a.example.com/index.html", "tag": None})
    assert "following links" in detail
