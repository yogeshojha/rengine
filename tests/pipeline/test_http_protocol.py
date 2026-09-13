from __future__ import annotations

from types import SimpleNamespace

import pytest

import tools.ffuf.client as ffuf_client
import tools.httpx.client as httpx_client
from shared.models.scan_context import HTTP_PROTOCOLS, PROBE_SCHEME
from shared.services.proxy_resolve import is_socks5
from stages.base import Stage

pytestmark = pytest.mark.pipeline

_BARE = ["a.example.com:443", "10.0.0.1:8080"]
_URLS = ["https://b.example.com/x", "http://c.example.com/y"]


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(httpx_client, "CLIToolRunner", lambda *a, **k: None)  # noqa: ARG005
    return httpx_client.HttpxClient


def _net(http_protocol: str):
    resolved = SimpleNamespace(proxy_url=None, headers={}, http_protocol=http_protocol)
    return Stage.net_options(SimpleNamespace(ctx=SimpleNamespace(resolved=resolved)))


def test_every_protocol_value_maps_to_a_scheme_or_to_neither():
    assert set(PROBE_SCHEME) | {"both"} == set(HTTP_PROTOCOLS)
    assert "both" not in PROBE_SCHEME


@pytest.mark.parametrize(
    ("http_protocol", "expected"),
    [("both", None), ("https_only", "https"), ("http_only", "http")],
)
def test_the_run_carries_the_scheme_its_context_asked_for(
    http_protocol: str, expected: str | None
):
    assert _net(http_protocol).probe_scheme == expected


def test_both_leaves_the_target_for_the_tool_to_decide(client):
    probe = client(probe_scheme=None)
    assert probe._scoped(_BARE) == _BARE
    assert "-no-fallback-scheme" not in probe._capture_args()


@pytest.mark.parametrize("scheme", ["https", "http"])
def test_a_restricted_run_names_the_scheme_on_every_bare_target(client, scheme: str):
    probe = client(probe_scheme=scheme)
    assert probe._scoped(_BARE) == [f"{scheme}://{t}" for t in _BARE]


def test_a_target_that_already_names_a_scheme_is_left_alone(client):
    assert client(probe_scheme="https")._scoped(_URLS) == _URLS


@pytest.mark.parametrize("scheme", ["https", "http"])
def test_a_restricted_run_stops_httpx_retrying_the_other_scheme(client, scheme: str):
    assert "-no-fallback-scheme" in client(probe_scheme=scheme)._capture_args()


@pytest.fixture
def ffuf(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(ffuf_client, "CLIToolRunner", lambda *a, **k: None)  # noqa: ARG005
    return ffuf_client.FfufClient


def _vhost_url(client) -> str:
    args = []

    def _run(**kwargs):
        args.extend(kwargs["args"])
        return SimpleNamespace(stdout="")

    client._runner = SimpleNamespace(run=_run)
    client.vhost("10.0.0.1", "example.com")
    return args[args.index("-u") + 1]


def test_a_vhost_sweep_defaults_to_http(ffuf):
    assert _vhost_url(ffuf(wordlist="w.txt")) == "http://10.0.0.1/"


@pytest.mark.parametrize("scheme", ["https", "http"])
def test_a_vhost_sweep_follows_the_run_restriction(ffuf, scheme: str):
    probe = ffuf(wordlist="w.txt", probe_scheme=scheme)
    assert _vhost_url(probe) == f"{scheme}://10.0.0.1/"


def _stage(follow_redirects: bool | None, proxy_url: str | None = None):
    resolved = SimpleNamespace(
        proxy_url=proxy_url,
        headers={},
        http_protocol="both",
        follow_redirects=follow_redirects,
    )
    return SimpleNamespace(ctx=SimpleNamespace(resolved=resolved))


@pytest.mark.parametrize("stage_default", [True, False])
def test_no_override_leaves_the_stage_setting_alone(stage_default: bool):
    assert Stage.follow_redirects(_stage(None), stage_default) is stage_default


@pytest.mark.parametrize(("override", "stage_default"), [(True, False), (False, True)])
def test_the_context_override_beats_the_stage_setting(
    override: bool, stage_default: bool
):
    assert Stage.follow_redirects(_stage(override), stage_default) is override


@pytest.mark.parametrize(
    ("proxy_url", "usable"),
    [
        ("socks5://10.0.0.1:1080", True),
        ("socks5h://u:p@10.0.0.1:1080", True),
        ("http://10.0.0.1:8080", False),
        ("https://10.0.0.1:8443", False),
        (None, False),
    ],
)
def test_a_socks5_only_tool_knows_which_proxies_it_can_carry(
    proxy_url: str | None, usable: bool
):
    assert is_socks5(proxy_url) is usable
