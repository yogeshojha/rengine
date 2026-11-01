"""Key checks for the providers whose test is one authenticated request."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from http import HTTPStatus

import httpx

from shared.definitions.api_keys import account_value, provider_name
from shared.enums.api_key import APIProvider
from shared.http import get_async_client

CHECK_TIMEOUT = 15.0
_REJECTED = frozenset({HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN})
_VALID = "API key is valid."


@dataclass(frozen=True)
class KeyCheck:
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, str] = field(default_factory=dict)
    method: str = "GET"
    rejected: frozenset[int] = _REJECTED
    refused: Callable[[dict], bool] | None = None
    describe: Callable[[dict], str | None] | None = None


def _number(value) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _shodan(body: dict) -> str | None:
    plan = body.get("plan")
    credits = _number(body.get("query_credits"))
    if not plan:
        return None
    if credits is None:
        return f"API key is valid. Plan {plan}."
    return f"API key is valid. Plan {plan}, {credits:,} query credits left."


def _censys(body: dict) -> str | None:
    balance = _number((body.get("result") or {}).get("balance"))
    return None if balance is None else f"API key is valid. {balance:,} credits left."


def _virustotal(body: dict) -> str | None:
    daily = ((body.get("data") or {}).get("api_requests_daily") or {}).get("user") or {}
    used, allowed = _number(daily.get("used")), _number(daily.get("allowed"))
    if used is None or allowed is None:
        return None
    return f"API key is valid. {max(allowed - used, 0):,} of {allowed:,} daily requests left."


def _alienvault(body: dict) -> str | None:
    username = body.get("username")
    return f"Signed in to AlienVault OTX as {username}." if username else None


def _fofa(body: dict) -> str | None:
    email = body.get("email")
    return f"Signed in to FOFA as {email}." if email else None


def _checks(provider: APIProvider, key: str, key_meta: dict | None) -> KeyCheck:  # noqa: PLR0911
    if provider is APIProvider.VIRUSTOTAL:
        return KeyCheck(
            f"https://www.virustotal.com/api/v3/users/{key}/overall_quotas",
            {"x-apikey": key},
            describe=_virustotal,
        )
    if provider is APIProvider.SHODAN:
        return KeyCheck(
            "https://api.shodan.io/api-info", params={"key": key}, describe=_shodan
        )
    if provider is APIProvider.CENSYS:
        org = account_value(provider, key_meta)
        path = (
            f"/v3/accounts/organizations/{org}/credits"
            if org
            else "/v3/accounts/users/credits"
        )
        return KeyCheck(
            f"https://api.platform.censys.io{path}",
            {"Authorization": f"Bearer {key}", "Accept": "application/json"},
            describe=_censys,
        )
    if provider is APIProvider.ALIENVAULT:
        return KeyCheck(
            "https://otx.alienvault.com/api/v1/users/me",
            {"X-OTX-API-KEY": key},
            describe=_alienvault,
        )
    if provider is APIProvider.URLSCAN:
        return KeyCheck(
            "https://urlscan.io/user/quotas/",
            {"API-Key": key},
            rejected=_REJECTED | {HTTPStatus.BAD_REQUEST},
        )
    if provider is APIProvider.CERTSPOTTER:
        return KeyCheck(
            "https://api.certspotter.com/v1/issuances?domain=example.com&include_subdomains=false",
            {"Authorization": f"Bearer {key}"},
        )
    if provider is APIProvider.FULLHUNT:
        return KeyCheck("https://fullhunt.io/api/v1/auth/status", {"X-API-KEY": key})
    if provider is APIProvider.LEAKIX:
        return KeyCheck(
            "https://leakix.net/api/subdomains/example.com",
            {"api-key": key, "Accept": "application/json"},
        )
    if provider is APIProvider.INTELX:
        host = account_value(provider, key_meta)
        return KeyCheck(f"https://{host}/authenticate/info", {"x-key": key})
    if provider is APIProvider.WHOISXMLAPI:
        return KeyCheck(
            "https://user.whoisxmlapi.com/user-service/account-balance",
            params={"apiKey": key},
        )
    if provider is APIProvider.FOFA:
        email = account_value(provider, key_meta)
        return KeyCheck(
            "https://fofa.info/api/v1/info/my",
            params={"email": email or "", "key": key},
            refused=lambda body: body.get("error") is True,
            describe=_fofa,
        )
    msg = f"No key check for {provider.value}."
    raise ValueError(msg)


CHECKED: tuple[APIProvider, ...] = (
    APIProvider.VIRUSTOTAL,
    APIProvider.SHODAN,
    APIProvider.CENSYS,
    APIProvider.ALIENVAULT,
    APIProvider.URLSCAN,
    APIProvider.CERTSPOTTER,
    APIProvider.FULLHUNT,
    APIProvider.LEAKIX,
    APIProvider.INTELX,
    APIProvider.WHOISXMLAPI,
    APIProvider.FOFA,
)


def _body(resp: httpx.Response) -> dict:
    try:
        body = resp.json()
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}


async def run_check(provider: APIProvider, key: str, key_meta: dict | None) -> dict:
    """One request with the key. A refusal raises ValueError with its reason."""
    name = provider_name(provider)
    check = _checks(provider, key, key_meta)
    try:
        async with get_async_client(
            follow_redirects=False, timeout=httpx.Timeout(CHECK_TIMEOUT)
        ) as client:
            resp = await client.request(
                check.method, check.url, headers=check.headers, params=check.params
            )
    except httpx.HTTPError:
        msg = f"{name} did not respond. Check the instance's outbound access."
        raise ValueError(msg) from None
    status = resp.status_code
    if status in check.rejected:
        msg = f"{name} refused the key."
        raise ValueError(msg)
    if status == HTTPStatus.TOO_MANY_REQUESTS:
        msg = f"{name} rate limited the test. Test again in a minute."
        raise ValueError(msg)
    if not resp.is_success:
        msg = f"{name} answered HTTP {status}."
        raise ValueError(msg)
    body = _body(resp)
    if check.refused is not None and check.refused(body):
        msg = f"{name} refused the key."
        raise ValueError(msg)
    message = (check.describe(body) if check.describe else None) or _VALID
    return {"message": message}


def tester(provider: APIProvider) -> Callable[[str, dict | None], Awaitable[dict]]:
    async def _test(key_value: str, key_meta: dict | None) -> dict:
        return await run_check(provider, key_value, key_meta)

    return _test


KEY_CHECKS = {provider: tester(provider) for provider in CHECKED}
