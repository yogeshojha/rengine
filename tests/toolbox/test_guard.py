from __future__ import annotations

import socket

import pytest

from toolbox import guard
from toolbox.base import ToolError

ANSWERS = {
    "127.0.0.1": ["127.0.0.1"],
    "169.254.169.254": ["169.254.169.254"],
    "10.0.0.1": ["10.0.0.1"],
    "::1": ["::1"],
    "fe80::1": ["fe80::1"],
    "intranet.example.com": ["10.1.2.3"],
    "split.example.com": ["1.1.1.1", "192.168.1.10"],
    "public.example.com": ["1.1.1.1", "2606:4700:4700::1111"],
}


@pytest.fixture(autouse=True)
def resolver(monkeypatch):
    def getaddrinfo(host, _port, *_args, **_kwargs):
        if host not in ANSWERS:
            raise socket.gaierror(socket.EAI_NONAME, "Name or service not known")
        return [(0, 0, 0, "", (address, 0)) for address in ANSWERS[host]]

    monkeypatch.setattr(guard.socket, "getaddrinfo", getaddrinfo)


@pytest.mark.parametrize(
    "value",
    [
        "127.0.0.1",
        "http://169.254.169.254/latest/meta-data/",
        "10.0.0.1:8080",
        "http://[::1]:8080/",
        "fe80::1",
        "intranet.example.com",
        "https://split.example.com/login",
    ],
)
def test_a_non_public_answer_is_refused(value):
    with pytest.raises(ToolError, match="Only publicly routable addresses"):
        guard.require_public(value)


def test_a_public_name_returns_every_address():
    assert guard.require_public("https://public.example.com/") == [
        "1.1.1.1",
        "2606:4700:4700::1111",
    ]


@pytest.mark.parametrize("value", ["", "https:///path"])
def test_an_empty_host_is_refused(value):
    with pytest.raises(ToolError, match="is not a valid host"):
        guard.require_public(value)


def test_a_name_that_does_not_resolve_is_refused():
    with pytest.raises(ToolError, match="does not resolve"):
        guard.require_public("missing.example.com")
