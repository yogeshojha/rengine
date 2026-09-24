from __future__ import annotations

import pytest

from shared.definitions.hygiene import HygieneCheck as C
from shared.services.web_hygiene import bigip_backend, evaluate, internal_addresses

pytestmark = pytest.mark.hygiene


def test_a_bigip_cookie_decodes_to_its_pool_member():
    assert bigip_backend("1677787402", "36895") == "10.1.1.100:8080"


def test_a_policy_header_naming_a_private_service_is_read():
    raw = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Security-Policy: connect-src 'self' http://192.168.200.101:3000\r\n"
    )
    assert internal_addresses(raw, None) == ["Content-Security-Policy: 192.168.200.101"]


def test_a_bigip_cookie_is_read_and_its_value_is_not():
    raw = "HTTP/1.1 200 OK\r\nSet-Cookie: BIGipServerpool=1677787402.36895.0000\r\n"
    assert internal_addresses(raw, None) == ["BIGipServerpool: 10.1.1.100:8080"]


def test_an_internal_name_in_a_header_is_read():
    raw = "HTTP/1.1 200 OK\r\nVia: 1.1 proxy01.corp\r\n"
    assert internal_addresses(raw, None) == ["Via: proxy01.corp"]


def test_links_and_quoted_values_in_a_page_are_read():
    body = (
        '<a href="http://192.168.77.150:81/">Portal</a>'
        '{"client_ip":"10.233.83.74","hostname":"api-58d5"}'
        "<img src='https://files.intranet/logo.png'>"
    )
    assert internal_addresses(None, body) == [
        "page: 192.168.77.150",
        "page: files.intranet",
        "page: 10.233.83.74",
    ]


def test_numbers_that_only_look_like_addresses_are_not_read():
    body = (
        '<path d="M10.105.318.85 10.09.23.85 5.5 10.1.2.3z"/>'
        '<a href="http://8.8.8.8/">dns</a> version 10.0.0.1 released'
    )
    assert internal_addresses(None, body) == []


def test_the_check_applies_to_every_response():
    found = evaluate(
        {},
        "HTTP/1.1 200 OK\r\n",
        scheme="https",
        status_code=200,
        content_type="text/html",
        body='<a href="http://10.1.15.10/">Gate pass</a>',
    )
    assert C.INTERNAL_ADDRESS.value in found.checked
    assert found.evidence[C.INTERNAL_ADDRESS.value] == "page: 10.1.15.10"
