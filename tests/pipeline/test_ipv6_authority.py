from __future__ import annotations

import pytest

from shared.definitions.endpoints import parse_url
from shared.services.endpoint_judge import root_of
from shared.utils.net import bracketed, host_port, split_host_port
from tools.httpx.parser import _host_of

pytestmark = pytest.mark.pipeline

_V6 = "2001:db8::1"


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        ("example.com", "example.com"),
        ("10.0.0.1", "10.0.0.1"),
        (_V6, f"[{_V6}]"),
        (f"[{_V6}]", f"[{_V6}]"),
    ],
)
def test_only_an_ipv6_literal_is_bracketed(host: str, expected: str):
    assert bracketed(host) == expected


def test_a_probe_target_names_a_port_a_tool_can_read():
    assert host_port("10.0.0.1", 443) == "10.0.0.1:443"
    assert host_port(_V6, 443) == f"[{_V6}]:443"


@pytest.mark.parametrize(
    ("authority", "expected"),
    [
        ("example.com:443", ("example.com", "443")),
        ("example.com", ("example.com", None)),
        ("10.0.0.1:80", ("10.0.0.1", "80")),
        (f"[{_V6}]:443", (_V6, "443")),
        (f"[{_V6}]", (_V6, None)),
        (_V6, (_V6, None)),
    ],
)
def test_an_authority_splits_back_into_host_and_port(
    authority: str, expected: tuple[str, str | None]
):
    assert split_host_port(authority) == expected


def test_host_port_round_trips_through_the_parser():
    assert split_host_port(host_port(_V6, 8443)) == (_V6, "8443")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("https://example.com:8443/x", "example.com"),
        (f"https://[{_V6}]:443/", _V6),
        (f"[{_V6}]:443", _V6),
        ("10.0.0.1:80", "10.0.0.1"),
    ],
)
def test_httpx_reads_the_host_back_off_its_own_target(value: str, expected: str):
    assert _host_of({"input": value}) == expected


def test_the_endpoint_layer_and_the_probe_agree_on_the_literal():
    assert parse_url(f"https://[{_V6}]:8443/a").url == f"https://[{_V6}]:8443/a"
    assert root_of("https", _V6, 8443) == f"https://[{_V6}]:8443"
    assert root_of("https", _V6, 443) == f"https://[{_V6}]"
