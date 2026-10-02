from typing import Any

import httpx

from shared.http import get_async_client
from shared.logging import get_logger

logger = get_logger(__name__)

BASE_URL = "https://api.viewdns.info"


class ViewDNSAPIError(Exception):
    """Base error for ViewDNS API calls."""


class ViewDNSAuthError(ViewDNSAPIError):
    """API key is invalid or missing."""


class ViewDNSRateLimitError(ViewDNSAPIError):
    """Rate limit or quota exhausted."""


class ViewDNSRejectedError(ViewDNSAPIError):
    """ViewDNS refused the query itself."""


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
        if 400 <= resp.status_code < 500:  # noqa: PLR2004
            msg = (
                f"ViewDNS refused the query on {endpoint} with HTTP {resp.status_code}"
            )
            raise ViewDNSRejectedError(msg)
        if resp.status_code != httpx.codes.OK:
            msg = f"ViewDNS returned HTTP {resp.status_code} on {endpoint}"
            raise ViewDNSAPIError(msg)

        try:
            data = resp.json()
        except ValueError as exc:
            msg = f"Unreadable response from {endpoint}"
            raise ViewDNSAPIError(msg) from exc
        if not isinstance(data, dict) or "response" not in data:
            msg = f"Unexpected response structure from {endpoint}"
            raise ViewDNSAPIError(msg)

        response_body = data["response"]
        if isinstance(response_body, dict) and response_body.get("error"):
            error_msg = str(response_body["error"])
            if "quota" in error_msg.lower() or "limit" in error_msg.lower():
                msg = f"Rate limit or quota exhausted on {endpoint}: {error_msg}"
                raise ViewDNSRateLimitError(msg)
            if "key" in error_msg.lower() or "auth" in error_msg.lower():
                msg = f"Authentication failed for {endpoint}: {error_msg}"
                raise ViewDNSAuthError(msg)
            msg = f"API error on {endpoint}: {error_msg}"
            raise ViewDNSAPIError(msg)

        return response_body

    async def _get(self, endpoint: str, **params) -> dict[str, Any]:
        try:
            async with get_async_client() as client:
                resp = await client.get(
                    f"{BASE_URL}/{endpoint}/", params=self._build_params(**params)
                )
        except httpx.HTTPError as exc:
            msg = f"ViewDNS could not be reached on {endpoint}: {type(exc).__name__}"
            raise ViewDNSAPIError(msg) from None
        return self._handle_response(resp, endpoint)

    async def ip_history(self, domain: str) -> dict[str, Any]:
        return await self._get("iphistory", domain=domain)

    async def reverse_ip(self, host: str) -> dict[str, Any]:
        return await self._get("reverseip", host=host)

    async def reverse_ns(self, ns: str) -> dict[str, Any]:
        return await self._get("reversens", ns=ns)

    async def reverse_whois(self, q: str) -> dict[str, Any]:
        return await self._get("reversewhois", q=q)
