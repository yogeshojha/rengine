from __future__ import annotations

import pytest

from stages.vulnerability_scan.scanners.echo_guard import (
    is_injection_echo_class,
    is_url_echo_false_positive,
    lenient_url_decode,
    request_body,
    request_target,
    response_body,
)
from tools.nuclei.parser import parse_finding

pytestmark = pytest.mark.pipeline


def _finding(
    template_id,
    tags,
    target,
    body,
    name="Some check",
    *,
    request=None,
    interaction=None,
    extracted=None,
    template=None,
):
    request = request or f"GET {target} HTTP/1.1\r\nHost: t.example\r\n\r\n"
    response = f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n{body}"
    record = {
        "template-id": template_id,
        "info": {"name": name, "tags": tags, "severity": "high"},
        "type": "http",
        "matched-at": f"https://t.example{target}",
        "url": f"https://t.example{target}",
        "request": request,
        "response": response,
    }
    if interaction:
        record["interaction"] = interaction
    if extracted:
        record["extracted-results"] = extracted
    if template:
        record["template"] = str(template)
    return parse_finding(record)


def _check(tmp_path, path, matchers):
    file = tmp_path / "check.yaml"
    file.write_text(
        "id: generic-os-command-injection\n"
        "info:\n  name: Command injection\n  severity: critical\n  tags: cmdi\n"
        f"http:\n  - method: GET\n    path:\n      - '{path}'\n"
        f"    matchers:\n{matchers}"
    )
    return file


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


def test_echoed_request_url_is_a_false_positive(tmp_path) -> None:
    target = "/search?q=;echo+wwwdata9231"
    body = f'<meta property="og:url" content="https://t.example{target}">'
    check = _check(
        tmp_path,
        "{{BaseURL}}/search?q=;echo+{{randstr}}",
        "      - type: word\n        words:\n          - '{{randstr}}'\n",
    )
    finding = _finding(
        "generic-os-command-injection", ["cmdi"], target, body, template=check
    )
    assert is_url_echo_false_positive(finding)


def test_percent_encoded_echo_is_caught_after_decoding(tmp_path) -> None:
    target = "/p?x=%3Becho%20marker4821"
    body = "<link rel=canonical href='/p?x=;echo marker4821'>"
    check = _check(
        tmp_path,
        "{{BaseURL}}/p?x=%3Becho%20{{marker}}",
        "      - type: word\n        words:\n          - '{{marker}}'\n",
    )
    finding = _finding("os-cmd-injection", ["cmdi"], target, body, template=check)
    assert is_url_echo_false_positive(finding)


def test_a_matcher_that_fires_outside_the_echo_is_kept(tmp_path) -> None:
    target = "/run?cmd=;id"
    body = f'<form action="{target}"></form><pre>uid=0(root) gid=0(root)</pre>'
    check = _check(
        tmp_path,
        "{{BaseURL}}/run?cmd=;id",
        "      - type: regex\n        regex:\n          - 'uid=\\d+\\(\\w+\\)'\n",
    )
    finding = _finding(
        "generic-os-command-injection", ["cmdi"], target, body, template=check
    )
    assert not is_url_echo_false_positive(finding)


def test_an_and_condition_needing_the_echo_is_dropped(tmp_path) -> None:
    target = "/run?cmd=;echo+marker5521"
    body = f'<title>Console</title><form action="{target}"></form>'
    check = _check(
        tmp_path,
        "{{BaseURL}}/run?cmd=;echo+{{marker}}",
        "      - type: word\n        condition: and\n        words:\n"
        "          - '<title>Console</title>'\n          - '{{marker}}'\n",
    )
    finding = _finding(
        "generic-os-command-injection", ["cmdi"], target, body, template=check
    )
    assert is_url_echo_false_positive(finding)


def test_a_check_that_does_not_read_is_kept() -> None:
    target = "/run?cmd=;id"
    body = f'<form action="{target}"></form><pre>uid=0(root) gid=0(root)</pre>'
    finding = _finding(
        "generic-os-command-injection",
        ["cmdi"],
        target,
        body,
        template="/nonexistent/check.yaml",
    )
    assert not is_url_echo_false_positive(finding)


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


def test_request_body_reads_past_the_header_break() -> None:
    assert request_body("POST /a HTTP/1.1\r\nHost: x\r\n\r\nip=1;id") == "ip=1;id"
    assert request_body("GET /a HTTP/1.1\r\nHost: x") == ""


def test_an_echoed_path_without_a_query_is_kept() -> None:
    target = "/cgi-bin/status"
    request = (
        f"GET {target} HTTP/1.1\r\nHost: t\r\n"
        "User-Agent: () { :; }; echo; /bin/cat /etc/passwd\r\n\r\n"
    )
    body = f'root:x:0:0:root:/root:/bin/bash <form action="{target}">'
    finding = _finding(
        "CVE-2014-6271", ["cve", "rce", "shellshock"], target, body, request=request
    )
    assert not is_url_echo_false_positive(finding)


def test_a_post_payload_with_an_echoed_path_is_kept() -> None:
    target = "/api/v1/ping?debug=1"
    request = f"POST {target} HTTP/1.1\r\nHost: t\r\n\r\nip=127.0.0.1;id"
    body = f'{{"endpoint":"{target}","out":"uid=0(root)"}}'
    finding = _finding("ping-cmdi", ["cmdi"], target, body, request=request)
    assert not is_url_echo_false_positive(finding)


def test_an_out_of_band_interaction_is_kept() -> None:
    target = "/search?q=;echo+wwwdata9231"
    body = f'<meta property="og:url" content="https://t.example{target}">'
    finding = _finding(
        "generic-os-command-injection",
        ["cmdi"],
        target,
        body,
        interaction={"protocol": "dns"},
    )
    assert not is_url_echo_false_positive(finding)


def test_an_extracted_value_outside_the_echo_is_kept() -> None:
    target = "/run?cmd=;id"
    body = f'<form action="{target}"></form><pre>uid=0(root) gid=0(root)</pre>'
    finding = _finding(
        "generic-os-command-injection",
        ["cmdi"],
        target,
        body,
        extracted=["uid=0(root)"],
    )
    assert not is_url_echo_false_positive(finding)


def test_an_extracted_value_only_inside_the_echo_is_dropped() -> None:
    target = "/run?cmd=;echo+marker7731"
    body = f'<form action="{target}"></form>'
    finding = _finding(
        "generic-os-command-injection",
        ["cmdi"],
        target,
        body,
        extracted=[";echo+marker7731"],
    )
    assert is_url_echo_false_positive(finding)
