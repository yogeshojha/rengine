from typing import Any

import httpx

from shared.http import get_async_client, get_sync_client
from shared.logging import get_logger

logger = get_logger(__name__)

BASE_URL = "https://api.viewdns.info"


class ViewDNSAPIError(Exception):
    """Base error for ViewDNS API calls."""


class ViewDNSAuthError(ViewDNSAPIError):
    """API key is invalid or missing."""


class ViewDNSRateLimitError(ViewDNSAPIError):
    """Rate limit or quota exhausted."""


class ViewDNSClient:
    """Low-level async client for ViewDNS.info API."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def _build_params(self, **kwargs) -> dict[str, str]:
        params = {"apikey": self._api_key, "output": "json"}
        params.update({k: v for k, v in kwargs.items() if v is not None})
        return params

    def _handle_response(self, resp: httpx.Response, endpoint: str) -> dict[str, Any]:
        if resp.status_code == 429:  # noqa: PLR2004
            msg = f"Rate limited on {endpoint}"
            raise ViewDNSRateLimitError(msg)
        if resp.status_code in (401, 403):
            msg = f"Authentication failed for {endpoint}"
            raise ViewDNSAuthError(msg)
        resp.raise_for_status()

        data = resp.json()
        if "response" not in data:
            msg = f"Unexpected response structure from {endpoint}"
            raise ViewDNSAPIError(msg)

        response_body = data["response"]
        if isinstance(response_body, dict) and response_body.get("error"):
            error_msg = response_body["error"]
            if "quota" in error_msg.lower() or "limit" in error_msg.lower():
                msg = f"Rate limit or quota exhausted on {endpoint}: {error_msg}"
                raise ViewDNSRateLimitError(msg)
            if "key" in error_msg.lower() or "auth" in error_msg.lower():
                msg = f"Authentication failed for {endpoint}: {error_msg}"
                raise ViewDNSAuthError(msg)
            msg = f"API error on {endpoint}: {error_msg}"
            raise ViewDNSAPIError(msg)

        return response_body

    async def ip_history(self, domain: str) -> dict[str, Any]:
        async with get_async_client() as client:
            resp = await client.get(
                f"{BASE_URL}/iphistory/",
                params=self._build_params(domain=domain),
            )
        return self._handle_response(resp, "iphistory")

    async def reverse_ip(self, host: str) -> dict[str, Any]:
        async with get_async_client() as client:
            resp = await client.get(
                f"{BASE_URL}/reverseip/",
                params=self._build_params(host=host),
            )
        return self._handle_response(resp, "reverseip")

    async def reverse_ns(self, ns: str) -> dict[str, Any]:
        async with get_async_client() as client:
            resp = await client.get(
                f"{BASE_URL}/reversens/",
                params=self._build_params(ns=ns),
            )
        return self._handle_response(resp, "reversens")

    async def reverse_whois(self, q: str) -> dict[str, Any]:
        async with get_async_client() as client:
            resp = await client.get(
                f"{BASE_URL}/reversewhois/",
                params=self._build_params(q=q),
            )
        return self._handle_response(resp, "reversewhois")

    # Sync variants for Celery workers

    def ip_history_sync(self, domain: str) -> dict[str, Any]:
        with get_sync_client() as client:
            resp = client.get(
                f"{BASE_URL}/iphistory/",
                params=self._build_params(domain=domain),
            )
        return self._handle_response(resp, "iphistory")

    def reverse_ip_sync(self, host: str) -> dict[str, Any]:
        with get_sync_client() as client:
            resp = client.get(
                f"{BASE_URL}/reverseip/",
                params=self._build_params(host=host),
            )
        return self._handle_response(resp, "reverseip")

    def reverse_ns_sync(self, ns: str) -> dict[str, Any]:
        with get_sync_client() as client:
            resp = client.get(
                f"{BASE_URL}/reversens/",
                params=self._build_params(ns=ns),
            )
        return self._handle_response(resp, "reversens")

    def reverse_whois_sync(self, q: str) -> dict[str, Any]:
        with get_sync_client() as client:
            resp = client.get(
                f"{BASE_URL}/reversewhois/",
                params=self._build_params(q=q),
            )
        return self._handle_response(resp, "reversewhois")
