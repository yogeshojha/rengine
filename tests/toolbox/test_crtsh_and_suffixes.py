from __future__ import annotations

import json
from datetime import date

import httpx
import pytest

from shared.definitions.domains import owning_zone, registrable_domain, target_zone
from shared.utils.net import redact_url_queries
from tools.crtsh import client as crtsh_client
from tools.crtsh.client import CrtShClient, CrtShError
from tools.crtsh.models import ROW_LIMIT, CrtShResult
from tools.crtsh.parser import parse_org_search
from tools.viewdns import client as viewdns_client
from tools.viewdns.client import (
    ViewDNSAPIError,
    ViewDNSAuthError,
    ViewDNSClient,
    ViewDNSRateLimitError,
    ViewDNSRejectedError,
)

SECRET = "f3282d0fdbe57be6244e5f8f20bed9ecd680b922"

SUFFIXES = [
    ("uber.com", "uber.com"),
    ("a.b.uber.com", "uber.com"),
    ("uber.com.kz", "uber.com.kz"),
    ("com.kz", ""),
    ("x.uber.co.uk", "uber.co.uk"),
    ("co.uk", ""),
    ("mof.gov.cy", "mof.gov.cy"),
    ("www.mof.gov.cy", "mof.gov.cy"),
    ("gov.cy", ""),
    ("police.gov.np", "police.gov.np"),
    ("gov.np", ""),
    ("anything.np", ""),
    ("www.city.kawasaki.jp", "city.kawasaki.jp"),
    ("a.b.kawasaki.jp", "a.b.kawasaki.jp"),
    ("www.ck", "www.ck"),
    ("x.ck", ""),
    ("example.com.br", "example.com.br"),
    ("*.example.com", "example.com"),
    ("EXAMPLE.COM.", "example.com"),
    ("1.2.3.4", ""),
    ("localhost", ""),
    ("", ""),
    ("autonomous.mobile", "autonomous.mobile"),
    ("sub.xn--mnchen-3ya.de", "xn--mnchen-3ya.de"),
]


@pytest.mark.parametrize(("host", "domain"), SUFFIXES)
def test_registrable_domain_reads_the_public_suffix_list(host, domain):
    assert registrable_domain(host) == domain


ZONES = [
    ("gov.cy", "gov.cy"),
    ("go.id", "go.id"),
    ("example.com", "example.com"),
    ("www.example.com", "example.com"),
    ("*.example.co.uk", "example.co.uk"),
    ("1.2.3.4", "1.2.3.4"),
]


@pytest.mark.parametrize(("value", "zone"), ZONES)
def test_a_target_owns_its_registrable_domain_or_itself_when_a_registry(value, zone):
    assert target_zone(value) == zone


OWNERS = [
    ("moh.gov.cy", "gov.cy"),
    ("gov.cy", "gov.cy"),
    ("kominfo.go.id", "go.id"),
    ("example.com", "example.com"),
    ("other.com", None),
    ("example.com.kz", None),
    ("", None),
]


@pytest.mark.parametrize(("apex", "zone"), OWNERS)
def test_owning_zone_matches_the_target_or_the_registry_above(apex, zone):
    zones = {target_zone(v) for v in ("gov.cy", "go.id", "www.example.com")}
    assert owning_zone(apex, zones) == zone


def _rows(*rows):
    return json.dumps(list(rows))


def _row(org, cn, day="2025-01-01T00:00:00"):
    return {"name_value": org, "common_name": cn, "not_before": day}


def test_parser_groups_certificates_by_organization():
    result = parse_org_search(
        _rows(
            _row("Uber Technologies, Inc.", "corp.uberinternal.com"),
            _row("Uber Technologies, Inc.", "api.uber.com"),
            _row("UBER TECHNOLOGIES, INC.", "*.uber.com"),
            _row("Uberduck, LLC", "uberduck.ai"),
        )
    )
    assert result.certs == 4
    names = {o.name: o for o in result.organizations}
    assert set(names["Uber Technologies, Inc."].domains) == {
        "uberinternal.com",
        "uber.com",
    }
    assert names["Uber Technologies, Inc."].certs == 2
    assert set(names["Uberduck, LLC"].domains) == {"uberduck.ai"}
    assert result.organizations[0].name == "Uber Technologies, Inc."


def test_parser_keeps_the_latest_certificate_date():
    result = parse_org_search(
        _rows(
            _row("Acme", "a.acme.com", "2020-01-01T00:00:00"),
            _row("Acme", "b.acme.com", "2024-06-30T12:00:00"),
            _row("Acme", "c.acme.com", "2022-01-01T00:00:00"),
        )
    )
    assert result.organizations[0].domains["acme.com"] == date(2024, 6, 30)


@pytest.mark.parametrize(
    "cn",
    ["PortSwigger CA", "103.69.127.108", "localhost", "", None, "co.uk", "*.com.kz"],
)
def test_parser_drops_names_that_are_not_registrable_domains(cn):
    result = parse_org_search(_rows({"name_value": "Acme", "common_name": cn}))
    assert result.organizations[0].domains == {}


@pytest.mark.parametrize(
    "payload",
    [
        "[BEGIN_HEADERS] Content-Type: application/json [END_HEADERS] error",
        "<html>502 Bad Gateway</html>",
        "",
        "{}",
        '{"error": "x"}',
        "null",
    ],
)
def test_parser_rejects_answers_that_are_not_a_list(payload):
    assert parse_org_search(payload) is None


def test_parser_skips_malformed_rows():
    result = parse_org_search(
        json.dumps(["x", 1, None, {}, {"name_value": ""}, _row("Acme", "acme.com")])
    )
    assert result.certs == 6
    assert [o.name for o in result.organizations] == ["Acme"]


def test_empty_list_is_a_real_answer():
    result = parse_org_search("[]")
    assert result is not None
    assert result.certs == 0


def test_row_limit_marks_the_answer_capped():
    assert CrtShResult(certs=ROW_LIMIT).capped
    assert not CrtShResult(certs=ROW_LIMIT - 1).capped


class _Redis:
    def __init__(self, broken=False):
        self.data = {}
        self.broken = broken

    def _check(self):
        if self.broken:
            msg = "redis down"
            raise ConnectionError(msg)

    async def get(self, key):
        self._check()
        return self.data.get(key)

    async def set(self, key, value, **_):
        self._check()
        self.data[key] = value


def _transport(monkeypatch, module, handler):
    def factory(**_):
        return httpx.AsyncClient(transport=httpx.MockTransport(handler))

    monkeypatch.setattr(module, "get_async_client", factory)


async def test_crtsh_client_caches_an_answer(monkeypatch):
    calls = []

    def handler(request):
        calls.append(request.url.params["O"])
        return httpx.Response(200, text=_rows(_row("Acme", "acme.com")))

    redis = _Redis()
    _transport(monkeypatch, crtsh_client, handler)
    monkeypatch.setattr(crtsh_client, "cache_client", lambda: redis)

    first = await CrtShClient().search_organization("Acme")
    second = await CrtShClient().search_organization("ACME")
    assert calls == ["Acme"]
    assert first.stored_at is None
    assert second.stored_at is not None
    assert set(second.organizations[0].domains) == {"acme.com"}


async def test_crtsh_client_works_without_redis(monkeypatch):
    _transport(
        monkeypatch,
        crtsh_client,
        lambda _: httpx.Response(200, text=_rows(_row("Acme", "acme.com"))),
    )
    monkeypatch.setattr(crtsh_client, "cache_client", lambda: _Redis(broken=True))
    result = await CrtShClient().search_organization("Acme")
    assert result.certs == 1


@pytest.mark.parametrize(
    ("response", "fragment"),
    [
        (httpx.Response(502, text="bad gateway"), "HTTP 502"),
        (httpx.Response(429, text="slow down"), "HTTP 429"),
        (httpx.Response(200, text="<html>error</html>"), "unreadable"),
    ],
)
async def test_crtsh_client_failures_are_crtsh_errors(monkeypatch, response, fragment):
    _transport(monkeypatch, crtsh_client, lambda _: response)
    monkeypatch.setattr(crtsh_client, "cache_client", _Redis)
    with pytest.raises(CrtShError) as exc:
        await CrtShClient().search_organization("Acme")
    assert fragment in str(exc.value)


@pytest.mark.parametrize(
    ("error", "fragment"),
    [
        (httpx.ReadTimeout("slow"), "did not answer within"),
        (httpx.ConnectError("refused"), "could not be reached"),
    ],
)
async def test_crtsh_client_transport_errors(monkeypatch, error, fragment):
    def handler(request):
        raise error

    _transport(monkeypatch, crtsh_client, handler)
    monkeypatch.setattr(crtsh_client, "cache_client", _Redis)
    with pytest.raises(CrtShError) as exc:
        await CrtShClient().search_organization("Acme")
    assert fragment in str(exc.value)


@pytest.mark.parametrize(
    ("status", "body", "error"),
    [
        (400, "bad", ViewDNSRejectedError),
        (404, "missing", ViewDNSRejectedError),
        (401, "no", ViewDNSAuthError),
        (403, "no", ViewDNSAuthError),
        (429, "slow", ViewDNSRateLimitError),
        (500, "boom", ViewDNSAPIError),
        (503, "boom", ViewDNSAPIError),
        (200, "not json", ViewDNSAPIError),
        (200, '{"nope": 1}', ViewDNSAPIError),
        (200, '{"response": {"error": "Invalid API key"}}', ViewDNSAuthError),
        (200, '{"response": {"error": "Query limit reached"}}', ViewDNSRateLimitError),
        (200, '{"response": {"error": "something else"}}', ViewDNSAPIError),
    ],
)
async def test_viewdns_errors_are_typed_and_never_carry_the_key(
    monkeypatch, status, body, error
):
    _transport(monkeypatch, viewdns_client, lambda _: httpx.Response(status, text=body))
    with pytest.raises(error) as exc:
        await ViewDNSClient(SECRET).reverse_whois("Uber")
    assert SECRET not in str(exc.value)
    assert SECRET not in repr(exc.value)
    assert exc.value.__cause__ is None or SECRET not in str(exc.value.__cause__)


async def test_viewdns_transport_errors_never_carry_the_url(monkeypatch):
    def handler(request):
        msg = f"cannot reach {request.url}"
        raise httpx.ConnectError(msg)

    _transport(monkeypatch, viewdns_client, handler)
    with pytest.raises(ViewDNSAPIError) as exc:
        await ViewDNSClient(SECRET).reverse_whois("Uber")
    assert SECRET not in str(exc.value)
    assert exc.value.__cause__ is None
    assert exc.value.__suppress_context__


async def test_viewdns_success_returns_the_response_body(monkeypatch):
    body = {"response": {"result_count": "1", "matches": [{"domain": "uber.com"}]}}
    _transport(monkeypatch, viewdns_client, lambda _: httpx.Response(200, json=body))
    assert await ViewDNSClient(SECRET).reverse_whois("Uber") == body["response"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            f"Client error for url 'https://api.viewdns.info/reversewhois/?apikey={SECRET}&q=Uber'",
            "Client error for url 'https://api.viewdns.info/reversewhois/?…'",
        ),
        ("GET http://h/p?token=abc#frag", "GET http://h/p?…#frag"),
        (
            "two https://a.io/x?k=1 and https://b.io/y?k=2",
            "two https://a.io/x?… and https://b.io/y?…",
        ),
        ("https://a.io/no-query", "https://a.io/no-query"),
        ("plain text", "plain text"),
        ("", ""),
    ],
)
def test_redact_url_queries(text, expected):
    assert redact_url_queries(text) == expected
