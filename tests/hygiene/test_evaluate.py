from __future__ import annotations

import pytest

from shared.definitions.hygiene import CHECK_KEYS, CHECKS
from shared.definitions.hygiene import HygieneCheck as C
from shared.services.web_hygiene import cookies_of, csp_directives, evaluate

pytestmark = pytest.mark.hygiene

_RAW_COOKIES = (
    "HTTP/1.1 200 OK\r\n"
    "Set-Cookie: cprelogin=no; HttpOnly; SameSite=Lax; "
    "expires=Thu, 01-Jan-1970 00:00:01 GMT; path=/; secure\r\n"
    "Set-Cookie: cpsession=abc; HttpOnly; path=/\r\n"
    "Set-Cookie: _ga=GA1.2; path=/\r\n"
)


def _run(headers, *, scheme="https", status=200, content_type="text/html", raw=None):
    return evaluate(
        headers, raw, scheme=scheme, status_code=status, content_type=content_type
    )


def test_no_response_applies_nothing():
    found = _run({"server": "nginx/1.2"}, status=None)
    assert found.checked == []
    assert found.issues == []


def test_hsts_applies_to_https_only():
    https = _run({})
    assert C.NO_HSTS in https.issues
    http = _run({}, scheme="http")
    assert C.NO_HSTS not in http.checked
    assert C.NO_HTTPS_REDIRECT in http.issues


def test_http_redirecting_to_https_passes():
    found = _run(
        {"location": "https://example.com/"},
        scheme="http",
        status=301,
        content_type=None,
    )
    assert C.NO_HTTPS_REDIRECT in found.checked
    assert C.NO_HTTPS_REDIRECT not in found.issues


def test_hsts_short_reads_max_age():
    short = _run({"strict_transport_security": "max-age=300"})
    assert C.HSTS_SHORT in short.issues
    assert short.evidence[C.HSTS_SHORT] == "max-age=300"
    long = _run({"strict_transport_security": "max-age=63072000; includeSubDomains"})
    assert C.HSTS_SHORT in long.checked
    assert C.HSTS_SHORT not in long.issues


def test_header_names_normalise_from_either_spelling():
    found = _run({"Strict-Transport-Security": "max-age=31536000"})
    assert C.NO_HSTS not in found.issues


def test_frame_protection_via_csp_frame_ancestors():
    found = _run(
        {"content_security_policy": "default-src 'self'; frame-ancestors 'none'"}
    )
    assert C.NO_FRAME_PROTECTION not in found.issues
    assert C.NO_CSP not in found.issues


def test_frame_checks_only_on_html_pages():
    found = _run({}, content_type="application/json")
    assert C.NO_FRAME_PROTECTION not in found.checked
    assert C.NO_CSP not in found.checked
    assert C.NO_NOSNIFF in found.issues


def test_csp_report_only_is_not_enforcing():
    found = _run({"content_security_policy_report_only": "default-src 'self'"})
    assert C.NO_CSP not in found.issues
    assert C.CSP_REPORT_ONLY in found.issues


def test_csp_unsafe_inline_is_theatre_only_without_nonce_or_strict_dynamic():
    plain = _run({"content_security_policy": "script-src 'self' 'unsafe-inline'"})
    assert C.CSP_UNSAFE_INLINE in plain.issues
    nonced = _run(
        {"content_security_policy": "script-src 'nonce-abc' 'unsafe-inline' https:"}
    )
    assert C.CSP_UNSAFE_INLINE not in nonced.issues
    assert C.CSP_WILDCARD_SCRIPT in nonced.issues
    strict = _run(
        {
            "content_security_policy": "script-src 'strict-dynamic' 'unsafe-inline' https:"
        }
    )
    assert C.CSP_UNSAFE_INLINE not in strict.issues
    assert C.CSP_WILDCARD_SCRIPT not in strict.issues


def test_csp_without_script_directive_does_not_govern_scripts():
    found = _run({"content_security_policy": "frame-ancestors 'self'"})
    assert C.CSP_UNSAFE_INLINE not in found.checked
    assert C.CSP_WILDCARD_SCRIPT not in found.checked


def test_csp_default_src_fallback_and_host_wildcards():
    found = _run({"content_security_policy": "default-src *.example.com 'self'"})
    assert C.CSP_WILDCARD_SCRIPT in found.checked
    assert C.CSP_WILDCARD_SCRIPT not in found.issues
    assert csp_directives("default-src *; default-src 'self'")["default-src"] == ["*"]


def test_cookies_read_from_raw_header_lines_not_joined_map():
    joined = {
        "set_cookie": (
            "cprelogin=no; HttpOnly; SameSite=Lax; expires=Thu, 01-Jan-1970 "
            "00:00:01 GMT; path=/; secure, cpsession=abc; HttpOnly; path=/, _ga=GA1.2; path=/"
        )
    }
    cookies = cookies_of(joined, _RAW_COOKIES)
    assert [c.name for c in cookies] == ["cprelogin", "cpsession", "_ga"]
    fallback = cookies_of(joined, None)
    assert [c.name for c in fallback] == ["cprelogin", "cpsession", "_ga"]


def test_cookie_secure_and_httponly_verdicts():
    found = _run({"set_cookie": "x"}, raw=_RAW_COOKIES)
    assert C.COOKIE_NO_SECURE in found.issues
    assert found.evidence[C.COOKIE_NO_SECURE] == "cpsession, _ga"
    assert C.COOKIE_NO_HTTPONLY in found.checked
    assert C.COOKIE_NO_HTTPONLY not in found.issues
    assert C.CACHEABLE_SESSION in found.issues


def test_session_cookie_naming_skips_csrf_and_analytics():
    raw = "Set-Cookie: csrftoken=1; path=/\r\nSet-Cookie: _ga=1; path=/\r\n"
    found = _run({}, raw=raw)
    assert C.COOKIE_NO_HTTPONLY not in found.checked
    assert C.CACHEABLE_SESSION not in found.checked
    raw = "Set-Cookie: JSESSIONID=1; path=/\r\n"
    found = _run({"cache_control": "no-store"}, raw=raw)
    assert C.COOKIE_NO_HTTPONLY in found.issues
    assert C.CACHEABLE_SESSION not in found.issues


def test_cookie_secure_not_judged_over_http():
    found = _run({}, scheme="http", raw="Set-Cookie: sid=1; path=/\r\n")
    assert C.COOKIE_NO_SECURE not in found.checked
    assert C.COOKIE_NO_HTTPONLY in found.issues


def test_cors_wildcard_and_credentials():
    public = _run({"access_control_allow_origin": "*"})
    assert C.CORS_ANY_ORIGIN in public.issues
    assert C.CORS_CREDENTIALS not in public.issues
    creds = _run(
        {
            "access_control_allow_origin": "null",
            "access_control_allow_credentials": "true",
        }
    )
    assert C.CORS_CREDENTIALS in creds.issues
    assert C.CORS_ANY_ORIGIN not in creds.issues
    exact = _run(
        {
            "access_control_allow_origin": "https://app.example.com",
            "access_control_allow_credentials": "true",
        }
    )
    assert exact.issues == [k for k in exact.issues if not k.startswith("cors_")]
    none = _run({})
    assert C.CORS_ANY_ORIGIN not in none.checked


def test_disclosure_checks():
    found = _run({"server": "nginx/1.18.0", "x_powered_by": "PHP/8.1"})
    assert C.SERVER_VERSION in found.issues
    assert found.evidence[C.SERVER_VERSION] == "nginx/1.18.0"
    assert found.evidence[C.RUNTIME_DISCLOSED] == "x-powered-by: PHP/8.1"
    bare = _run({"server": "cloudflare"})
    assert C.SERVER_VERSION in bare.checked
    assert C.SERVER_VERSION not in bare.issues
    assert C.RUNTIME_DISCLOSED in bare.checked
    assert C.RUNTIME_DISCLOSED not in bare.issues


def test_every_verdict_key_is_a_declared_check():
    found = _run(
        {
            "server": "nginx/1.18.0",
            "x_powered_by": "PHP",
            "access_control_allow_origin": "*",
            "content_security_policy": "script-src 'unsafe-inline' *",
        },
        raw="Set-Cookie: sid=1\r\n",
    )
    assert set(found.checked) <= set(CHECK_KEYS)
    assert len(found.checked) == len(set(found.checked))
    assert len({c.key for c in CHECKS}) == len(CHECKS)
