from __future__ import annotations

import pytest

from stages.vulnerability_scan.scanners.echo_guard import (
    is_injection_echo_class,
    is_url_echo_false_positive,
    lenient_url_decode,
    request_target,
    response_body,
)
from tools.nuclei.parser import parse_finding

pytestmark = pytest.mark.pipeline


def _finding(template_id, tags, target, body, name="Some check"):
    request = f"GET {target} HTTP/1.1\r\nHost: t.example\r\n\r\n"
    response = f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n{body}"
    return parse_finding(
        {
            "template-id": template_id,
            "info": {"name": name, "tags": tags, "severity": "high"},
            "type": "http",
            "matched-at": f"https://t.example{target}",
            "url": f"https://t.example{target}",
            "request": request,
            "response": response,
        }
    )


def test_request_target_reads_the_start_line() -> None:
    assert request_target("POST /a?b=c HTTP/1.1\r\nHost: x\r\n\r\n") == "/a?b=c"
    assert request_target("") == ""
    assert request_target("garbage") == ""


def test_response_body_splits_on_the_header_break() -> None:
    assert response_body("HTTP/1.1 200 OK\r\nX: y\r\n\r\nBODY") == "BODY"
    assert response_body("no headers here") == "no headers here"


def test_lenient_decode_leaves_a_malformed_escape() -> None:
    assert lenient_url_decode("/a%2Fb+c") == "/a/b c"
    assert lenient_url_decode("/50%") == "/50%"


def test_injection_class_matches_command_and_rce_but_not_xss_or_oast() -> None:
    assert is_injection_echo_class("apache-cmdi", None, ["cmdi"])
    assert is_injection_echo_class("some-rce-check", None, [])
    assert is_injection_echo_class("cve-2014-6271", None, ["shellshock"])
    assert not is_injection_echo_class("reflected-xss", None, ["xss"])
    assert not is_injection_echo_class("log4j-rce", None, ["oast"])
    assert not is_injection_echo_class("wordpress-detect", None, ["tech"])


def test_echoed_request_url_is_a_false_positive() -> None:
    target = "/search?q=;echo+wwwdata9231"
    body = f'<meta property="og:url" content="https://t.example{target}">'
    finding = _finding("generic-os-command-injection", ["cmdi"], target, body)
    assert is_url_echo_false_positive(finding)


def test_percent_encoded_echo_is_caught_after_decoding() -> None:
    target = "/p?x=%3Becho%20marker4821"
    body = "<link rel=canonical href='/p?x=;echo marker4821'>"
    finding = _finding("os-cmd-injection", ["cmdi"], target, body)
    assert is_url_echo_false_positive(finding)


def test_real_command_output_is_kept() -> None:
    target = "/cgi?x=;id"
    body = "uid=33(www-data) gid=33(www-data) groups=33(www-data)"
    finding = _finding("shellshock", ["cmdi", "shellshock"], target, body)
    assert not is_url_echo_false_positive(finding)


def test_xss_reflection_is_never_filtered() -> None:
    target = "/s?q=<script>alert(1)</script>"
    body = "<div><script>alert(1)</script></div>"
    finding = _finding("reflected-xss", ["xss"], target, body)
    assert not is_url_echo_false_positive(finding)


def test_a_short_target_does_not_trigger() -> None:
    finding = _finding("os-command-injection", ["cmdi"], "/a", "/a echoed here")
    assert not is_url_echo_false_positive(finding)
