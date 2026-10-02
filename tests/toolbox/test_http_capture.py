"""The toolbox screenshot holds headless Chrome to the checked host."""

from __future__ import annotations

import contextlib

import pytest

from toolbox.tools import http_probe
from tools.runner import StreamOutcome


class _Client:
    def __init__(self, built: list[list[str]], **kwargs) -> None:
        built.append(kwargs.get("extra_args") or [])

    @contextlib.contextmanager
    def stream_capture(self, _targets):
        yield StreamOutcome(records=iter(()), return_code=0)


class _Built:
    def __init__(self) -> None:
        self.built: list[list[str]] = []

    def __call__(self, **kwargs) -> _Client:
        return _Client(self.built, **kwargs)


@pytest.fixture
def client(monkeypatch):
    factory = _Built()
    monkeypatch.setattr(http_probe, "HttpxClient", factory)
    return factory


def _headless(extra: list[str]) -> list[str]:
    return [extra[i + 1] for i, token in enumerate(extra) if token == "-ho"]


def test_hostname_is_pinned_to_the_checked_address(client, monkeypatch):
    monkeypatch.setattr(
        http_probe, "require_public", lambda _: ["2606:2800::1", "93.184.216.34"]
    )
    http_probe._capture({"status_code": 200, "url": "https://example.com/"}, True)
    assert _headless(client.built[0]) == [
        f"proxy-server={http_probe.DEAD_PROXY}",
        "proxy-bypass-list=example.com;<-loopback>",
        "host-resolver-rules=MAP example.com 93.184.216.34",
    ]
    assert "-deny" in client.built[0]


def test_address_literal_is_the_only_bypass(client, monkeypatch):
    monkeypatch.setattr(http_probe, "require_public", lambda _: ["2606:2800::1"])
    http_probe._capture(
        {"status_code": 200, "url": "http://[2606:2800::1]:8080/"}, True
    )
    assert _headless(client.built[0]) == [
        f"proxy-server={http_probe.DEAD_PROXY}",
        "proxy-bypass-list=[2606:2800::1];<-loopback>",
    ]


@pytest.mark.parametrize(
    "url", ["https://a;*.example.com/", "https://example.com./", "https://a b.example/"]
)
def test_host_outside_the_rule_syntax_is_not_rendered(client, monkeypatch, url):
    monkeypatch.setattr(http_probe, "require_public", lambda _: ["93.184.216.34"])
    assert http_probe._capture({"status_code": 200, "url": url}, True) is None
    assert client.built == []
