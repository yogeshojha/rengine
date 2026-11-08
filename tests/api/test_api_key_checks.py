from __future__ import annotations

import httpx
import pytest
from fastapi import HTTPException

from app.api.v1.api_keys import API_KEY_TESTERS, list_providers
from app.api.v1.api_keys import test_api_key as run_key_test
from app.services import api_key_checks
from app.services.api_key_checks import CHECKED, run_check
from shared.definitions.api_keys import SUBFINDER_SOURCES
from shared.enums.api_key import APIProvider
from shared.models.api_key import APIKey, APIKeyCreate, APIKeyUpdate
from shared.models.user import User
from shared.services.api_key.async_api_key import APIKeyService
from shared.services.scan_resolve import MASK
from shared.utils.crypto import encrypt_secret, try_decrypt

pytestmark = pytest.mark.api

KEY = "k3y-0000-secret"
ORG = "1d8f0c2a-0000-4000-8000-000000000001"


class _Wire:
    def __init__(self, monkeypatch, response: httpx.Response | Exception) -> None:
        self.requests: list[httpx.Request] = []
        self.response = response

        def handler(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            if isinstance(self.response, Exception):
                raise self.response
            return self.response

        def client(**overrides):
            assert overrides["follow_redirects"] is False
            return httpx.AsyncClient(transport=httpx.MockTransport(handler))

        monkeypatch.setattr(api_key_checks, "get_async_client", client)

    @property
    def url(self) -> httpx.URL:
        return self.requests[0].url


# ---------- the checks ----------


@pytest.mark.parametrize(
    ("provider", "body", "message"),
    [
        (
            APIProvider.SHODAN,
            {"plan": "dev", "query_credits": 100},
            "API key is valid. Plan dev, 100 query credits left.",
        ),
        (APIProvider.SHODAN, {"plan": "oss"}, "API key is valid. Plan oss."),
        (
            APIProvider.CENSYS,
            {"result": {"balance": 87, "resets_at": "2026-12-01T00:00:00Z"}},
            "API key is valid. 87 credits left.",
        ),
        (
            APIProvider.VIRUSTOTAL,
            {"data": {"api_requests_daily": {"user": {"used": 20, "allowed": 500}}}},
            "API key is valid. 480 of 500 daily requests left.",
        ),
        (
            APIProvider.ALIENVAULT,
            {"username": "ops"},
            "Signed in to AlienVault OTX as ops.",
        ),
        (
            APIProvider.FOFA,
            {"error": False, "email": "a@b.co"},
            "Signed in to FOFA as a@b.co.",
        ),
        (APIProvider.URLSCAN, {"limits": {}}, "API key is valid."),
        (APIProvider.CENSYS, {"unexpected": True}, "API key is valid."),
    ],
)
async def test_an_accepted_key_says_what_the_provider_reported(
    monkeypatch, provider, body, message
):
    _Wire(monkeypatch, httpx.Response(200, json=body))
    result = await run_check(provider, KEY, {"email": "a@b.co"})
    assert result == {"message": message}


@pytest.mark.parametrize("provider", CHECKED)
@pytest.mark.parametrize("status", [401, 403])
async def test_a_refused_key_is_named_refused(monkeypatch, provider, status):
    _Wire(monkeypatch, httpx.Response(status, text="<html>no</html>"))
    with pytest.raises(ValueError, match="refused the key") as exc:
        await run_check(provider, KEY, {"email": "a@b.co"})
    assert KEY not in str(exc.value)


async def test_urlscan_reads_a_malformed_key_as_refused(monkeypatch):
    _Wire(monkeypatch, httpx.Response(400, json={"message": "Invalid API key format"}))
    with pytest.raises(ValueError, match=r"urlscan\.io refused the key"):
        await run_check(APIProvider.URLSCAN, KEY, None)


async def test_fofa_reads_an_error_body_as_refused(monkeypatch):
    _Wire(
        monkeypatch,
        httpx.Response(200, json={"error": True, "errmsg": "[-700] invalid"}),
    )
    with pytest.raises(ValueError, match="FOFA refused the key"):
        await run_check(APIProvider.FOFA, KEY, {"email": "a@b.co"})


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (
            httpx.Response(429),
            "VirusTotal rate limited the test. Test again in a minute.",
        ),
        (httpx.Response(503), "VirusTotal answered HTTP 503."),
        (
            httpx.Response(302, headers={"location": "https://attacker.example/"}),
            "VirusTotal answered HTTP 302.",
        ),
        (
            httpx.ConnectError(f"https://www.virustotal.com/api/v3/users/{KEY}"),
            "VirusTotal did not respond. Check the instance's outbound access.",
        ),
    ],
)
async def test_a_failed_check_names_the_cause_without_the_key(
    monkeypatch, response, message
):
    wire = _Wire(monkeypatch, response)
    with pytest.raises(ValueError, match="VirusTotal") as exc:
        await run_check(APIProvider.VIRUSTOTAL, KEY, None)
    assert str(exc.value) == message
    assert exc.value.__cause__ is None
    assert len(wire.requests) == 1


async def test_censys_reads_the_organization_balance_when_one_is_stored(monkeypatch):
    wire = _Wire(monkeypatch, httpx.Response(200, json={"result": {"balance": 1}}))
    await run_check(APIProvider.CENSYS, KEY, {"organization_id": ORG})
    assert wire.url.path == f"/v3/accounts/organizations/{ORG}/credits"
    assert wire.requests[0].headers["authorization"] == f"Bearer {KEY}"

    wire = _Wire(monkeypatch, httpx.Response(200, json={"result": {"balance": 1}}))
    await run_check(APIProvider.CENSYS, KEY, None)
    assert wire.url.path == "/v3/accounts/users/credits"


async def test_intelligence_x_is_asked_at_the_stored_host_or_the_free_one(monkeypatch):
    wire = _Wire(monkeypatch, httpx.Response(200, json={}))
    await run_check(APIProvider.INTELX, KEY, None)
    assert wire.url.host == "free.intelx.io"
    wire = _Wire(monkeypatch, httpx.Response(200, json={}))
    await run_check(APIProvider.INTELX, KEY, {"host": "2.intelx.io"})
    assert wire.url.host == "2.intelx.io"
    assert wire.requests[0].headers["x-key"] == KEY


@pytest.mark.parametrize("provider", CHECKED)
async def test_every_check_is_one_https_request(monkeypatch, provider):
    wire = _Wire(monkeypatch, httpx.Response(200, json={}))
    await run_check(provider, KEY, {"email": "a@b.co"})
    assert len(wire.requests) == 1
    assert wire.url.scheme == "https"


def test_every_check_is_a_tester():
    assert set(CHECKED) <= set(API_KEY_TESTERS)


# ---------- the router ----------


async def _admin(estate) -> User:
    return await estate.session.get(User, estate.user_id)


async def test_providers_serve_the_account_field_and_the_setup_flag(estate, flush_only):
    providers = {
        p.provider: p
        for p in await list_providers(
            _current_user=await _admin(estate), service=APIKeyService(flush_only)
        )
    }
    assert set(SUBFINDER_SOURCES) <= set(providers)
    fofa = providers[APIProvider.FOFA]
    assert (fofa.account.field, fofa.account.required) == ("email", True)
    intelx = providers[APIProvider.INTELX]
    assert (intelx.account.required, intelx.account.default) == (
        False,
        "free.intelx.io",
    )
    assert providers[APIProvider.HACKERONE].account.field == "username"
    assert providers[APIProvider.VIRUSTOTAL].account is None
    assert providers[APIProvider.VIRUSTOTAL].setup
    assert not providers[APIProvider.ZOOMEYE].setup
    assert providers[APIProvider.SHODAN].testable
    assert not providers[APIProvider.ZOOMEYE].testable


async def test_a_test_through_the_router_masks_an_echoed_key(
    estate, flush_only, monkeypatch
):
    key = APIKey(provider=APIProvider.SHODAN, key_value=encrypt_secret(KEY))
    flush_only.add(key)
    await flush_only.flush()

    async def echo(key_value, _meta):
        msg = f"Shodan said no to {key_value}"
        raise ValueError(msg)

    monkeypatch.setitem(API_KEY_TESTERS, APIProvider.SHODAN, echo)
    body = await run_key_test(
        str(key.id),
        _current_user=await _admin(estate),
        service=APIKeyService(flush_only),
    )
    assert body["success"] is False
    assert KEY not in body["message"]
    assert MASK in body["message"]
    assert key.last_test_ok is False


# ---------- storing a key ----------


async def test_a_key_is_stored_trimmed_with_its_account_alone(estate, flush_only):
    read = await APIKeyService(flush_only).create_key(
        APIKeyCreate(
            provider=APIProvider.FOFA,
            key_value="  fofakey  ",
            key_meta={"email": " ops@example.com ", "smuggled": "x"},
        )
    )
    row = await flush_only.get(APIKey, read.id)
    assert try_decrypt(row.key_value) == "fofakey"
    assert row.key_meta == {"email": "ops@example.com"}


@pytest.mark.parametrize(
    ("provider", "key", "meta", "detail"),
    [
        (APIProvider.FOFA, "k", None, "FOFA requires the account email."),
        (APIProvider.FOFA, "a:b", {"email": "a@b.co"}, "contains a colon"),
        (APIProvider.VIRUSTOTAL, "two words", None, "spaces or control characters"),
        (APIProvider.VIRUSTOTAL, "line\nbreak", None, "spaces or control characters"),
        (APIProvider.INTELX, "k", {"host": "attacker.example"}, "intelx.io host"),
        (APIProvider.ZOOMEYE, "k", {"host": "127.0.0.1"}, "zoomeye.ai or zoomeye.hk"),
        (APIProvider.CENSYS, "k", {"organization_id": "nope"}, "UUID"),
        (APIProvider.HACKERONE, "k", {"username": ""}, "requires the username"),
        (APIProvider.SHODAN, f"x{MASK}", None, "masked value"),
    ],
)
async def test_a_key_that_cannot_be_used_is_refused(
    estate, flush_only, provider, key, meta, detail
):
    with pytest.raises(HTTPException) as exc:
        await APIKeyService(flush_only).create_key(
            APIKeyCreate(provider=provider, key_value=key, key_meta=meta)
        )
    assert exc.value.status_code == 400
    assert detail in exc.value.detail


async def test_changing_the_account_clears_the_last_test(estate, flush_only):
    service = APIKeyService(flush_only)
    read = await service.create_key(
        APIKeyCreate(provider=APIProvider.CENSYS, key_value="pat", key_meta=None)
    )
    row = await flush_only.get(APIKey, read.id)
    await service.record_test(row, True, "API key is valid.")

    same = await service.update_key(
        str(read.id), APIKeyUpdate(key_meta={"organization_id": ""})
    )
    assert same.last_test_ok is True

    moved = await service.update_key(
        str(read.id), APIKeyUpdate(key_meta={"organization_id": ORG})
    )
    assert moved.key_meta == {"organization_id": ORG}
    assert moved.last_test_ok is None
    assert try_decrypt(row.key_value) == "pat"


async def test_an_update_is_validated_like_a_create(estate, flush_only):
    service = APIKeyService(flush_only)
    read = await service.create_key(
        APIKeyCreate(provider=APIProvider.INTELX, key_value="ik", key_meta=None)
    )
    with pytest.raises(HTTPException) as exc:
        await service.update_key(
            str(read.id), APIKeyUpdate(key_meta={"host": "evil.example"})
        )
    assert exc.value.status_code == 400
    with pytest.raises(HTTPException):
        await service.update_key(str(read.id), APIKeyUpdate(key_value="has space"))
    kept = await service.update_key(str(read.id), APIKeyUpdate(key_value=f"ik{MASK}"))
    row = await flush_only.get(APIKey, kept.id)
    assert try_decrypt(row.key_value) == "ik"


async def test_a_query_value_is_encoded(monkeypatch):
    wire = _Wire(monkeypatch, httpx.Response(200, json={"error": False, "email": "x"}))
    await run_check(APIProvider.FOFA, "k&debug=1", {"email": "ops+recon@corp.com"})
    assert wire.url.params["email"] == "ops+recon@corp.com"
    assert wire.url.params["key"] == "k&debug=1"
    assert "debug" not in wire.url.params
