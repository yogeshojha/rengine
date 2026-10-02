from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import httpx
import pytest

from shared import http
from shared.definitions.bounty_feed import FEEDS
from shared.services import bounty_feed, nvd_corpus, threat_intel, vulnx
from shared.services.ai import client as ai_client
from shared.services.ai.config import AIConfig
from shared.services.bounty_providers import base as bounty_base

pytestmark = pytest.mark.pipeline

PROXY = "http://egress.internal:3128"


def _settings(proxy: str = PROXY) -> SimpleNamespace:
    return SimpleNamespace(
        EGRESS_PROXY_URL=proxy, EGRESS_TIMEOUT=30.0, EGRESS_USER_AGENT="ua"
    )


def _mock(handler):
    def factory(**kwargs):
        kwargs.pop("transport", None)
        kwargs.pop("proxy", None)
        return httpx.Client(transport=httpx.MockTransport(handler), **kwargs)

    return factory


def test_the_shared_client_carries_the_egress_proxy(monkeypatch):
    monkeypatch.setattr(http, "base_settings", _settings)
    assert http._base_kwargs()["proxy"] == PROXY
    assert http.egress_proxy() == PROXY
    monkeypatch.setattr(http, "base_settings", lambda: _settings(""))
    assert "proxy" not in http._base_kwargs()
    assert http.egress_proxy() is None


def test_a_feed_download_goes_through_the_shared_client(monkeypatch):
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, content=b"x" * 10)

    monkeypatch.setattr(http, "get_sync_client", _mock(handler))
    with threat_intel._download("https://feeds.example/kev.json", "kev.data") as (
        path,
        size,
    ):
        assert size == 10
        assert path.read_bytes() == b"x" * 10
    assert [str(r.url) for r in seen] == ["https://feeds.example/kev.json"]
    assert seen[0].headers["User-Agent"] != "reNgine"


def test_a_capped_download_is_refused(monkeypatch, tmp_path):
    monkeypatch.setattr(
        http,
        "get_sync_client",
        _mock(lambda _r: httpx.Response(200, content=b"x" * 10)),
    )
    with pytest.raises(ValueError, match="exceeded 4 bytes"):
        http.download("https://feeds.example/f", tmp_path / "f", timeout=5, max_bytes=4)


def test_the_current_year_missing_from_the_mirror_is_unpublished(monkeypatch, tmp_path):
    monkeypatch.setattr(http, "get_sync_client", _mock(lambda _r: httpx.Response(404)))
    with pytest.raises(httpx.HTTPStatusError) as caught:
        nvd_corpus._fetch("CVE-2026.json.xz", tmp_path / "f")
    year = datetime.now(UTC).year
    assert nvd_corpus._unpublished(caught.value, year, year)
    assert not nvd_corpus._unpublished(caught.value, year - 1, year)


def test_a_feed_status_is_named(monkeypatch):
    monkeypatch.setattr(http, "get_sync_client", _mock(lambda _r: httpx.Response(503)))
    with pytest.raises(bounty_feed.FeedError, match="returned 503"):
        bounty_feed._download(FEEDS[0])


def test_vulnx_reads_the_rate_limit(monkeypatch):
    monkeypatch.setattr(
        vulnx,
        "get_sync_client",
        _mock(lambda _r: httpx.Response(429, headers={"x-ratelimit-reset": "123.0"})),
    )
    budget = vulnx.Budget()
    with pytest.raises(vulnx.RateLimitedError):
        vulnx._request("/CVE-2024-1", {}, "key", budget)
    assert (budget.remaining, budget.reset_at) == (0, 123.0)


@pytest.mark.parametrize(
    ("status", "body", "error"),
    [
        (401, b"", bounty_base.CredentialsError),
        (403, b'{"code":"FORBID001"}', bounty_base.AccessDeniedError),
        (500, b"", bounty_base.BountyProviderError),
    ],
)
def test_a_platform_refusal_maps_to_its_error(monkeypatch, status, body, error):
    monkeypatch.setattr(
        bounty_base,
        "get_sync_client",
        _mock(lambda _r: httpx.Response(status, content=body)),
    )
    client = bounty_base.JsonClient(label="P", headers={}, denied_marker="FORBID001")
    with pytest.raises(error):
        client.get("https://api.example/programs")


def test_a_rate_limited_platform_read_is_retried(monkeypatch):
    answers = iter([httpx.Response(429), httpx.Response(200, json={"data": [1]})])
    monkeypatch.setattr(bounty_base, "get_sync_client", _mock(lambda _r: next(answers)))
    monkeypatch.setattr(bounty_base.time, "sleep", lambda _s: None)
    client = bounty_base.JsonClient(label="P", headers={})
    assert client.get("https://api.example/programs", {"page": 1}) == {"data": [1]}


@pytest.mark.parametrize(
    ("provider", "expected"),
    [
        ("anthropic", PROXY),
        ("openai", PROXY),
        ("google", PROXY),
        ("openai_compatible", None),
    ],
)
def test_ai_calls_take_the_egress_proxy_except_a_local_server(
    monkeypatch, provider, expected
):
    monkeypatch.setattr(ai_client, "egress_proxy", lambda: PROXY)
    cfg = AIConfig(
        provider=provider, api_key="k", model="m", fast_model="m", features={}
    )
    assert ai_client.provider_proxy(cfg) == expected
