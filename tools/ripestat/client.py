"""RIPEstat HTTP client for GET /data/{endpoint}/data.json."""

from typing import Any

import httpx

from shared.http import get_async_client, get_sync_client

BASE_URL = "https://stat.ripe.net/data"
SOURCE_APP = ""


class RIPEStatAPIError(Exception):
    """Base error for RIPEstat API calls."""


class RIPEStatRateLimitError(RIPEStatAPIError):
    """Rate limit exceeded (429 or data-level throttle)."""


class RIPEStatInvalidResourceError(RIPEStatAPIError):
    """RIPEstat refused the resource."""


class RIPEStatClient:
    """Low-level HTTP client for RIPEstat API."""

    def __init__(self, proxy_url: str | None = None) -> None:
        self._proxy_url = proxy_url

    def _egress(self) -> httpx.Client:
        """The scan's proxy when the run names one, the instance egress otherwise."""
        if self._proxy_url:
            return get_sync_client(proxy=self._proxy_url)
        return get_sync_client()

    def _build_params(self, resource: str, **kwargs) -> dict[str, str]:
        params = {
            "resource": resource,
            "sourceapp": SOURCE_APP,
        }
        params.update({k: v for k, v in kwargs.items() if v is not None})
        return params

    def _handle_response(self, resp: httpx.Response, endpoint: str) -> dict[str, Any]:
        if resp.status_code == 429:  # noqa: PLR2004
            msg = f"RIPEstat rate limit on {endpoint}"
            raise RIPEStatRateLimitError(msg)
        if 400 <= resp.status_code < 500:  # noqa: PLR2004
            msg = f"RIPEstat rejected the resource for {endpoint}"
            raise RIPEStatInvalidResourceError(msg)
        if resp.status_code >= 500:  # noqa: PLR2004
            msg = f"RIPEstat returned {resp.status_code} for {endpoint}"
            raise RIPEStatAPIError(msg)

        body = resp.json()

        # RIPEstat wraps errors in status/status_code fields
        status_code = body.get("status_code", 200)
        if status_code == 429:  # noqa: PLR2004
            msg = f"RIPEstat rate limit (data-level) on {endpoint}"
            raise RIPEStatRateLimitError(msg)
        if status_code >= 400:  # noqa: PLR2004
            msg = f"RIPEstat error on {endpoint}: {body.get('message', 'unknown')}"
            raise RIPEStatAPIError(msg)

        if "data" not in body:
            msg = f"Unexpected response structure from {endpoint}: missing 'data' key"
            raise RIPEStatAPIError(msg)

        return body["data"]

    # fastapi async methods

    async def searchcomplete(self, query: str) -> dict[str, Any]:
        async with get_async_client() as client:
            resp = await client.get(
                f"{BASE_URL}/searchcomplete/data.json",
                params=self._build_params(query),
            )
        return self._handle_response(resp, "searchcomplete")

    # celery sync methods

    def announced_prefixes_sync(self, asn: str) -> dict[str, Any]:
        with self._egress() as client:
            resp = client.get(
                f"{BASE_URL}/announced-prefixes/data.json",
                params=self._build_params(asn),
            )
        return self._handle_response(resp, "announced-prefixes")

    def asn_neighbours_sync(self, asn: str) -> dict[str, Any]:
        with self._egress() as client:
            resp = client.get(
                f"{BASE_URL}/asn-neighbours/data.json",
                params=self._build_params(asn),
            )
        return self._handle_response(resp, "asn-neighbours")

    def as_overview_sync(self, asn: str) -> dict[str, Any]:
        with self._egress() as client:
            resp = client.get(
                f"{BASE_URL}/as-overview/data.json",
                params=self._build_params(asn),
            )
        return self._handle_response(resp, "as-overview")

    def network_info_sync(self, ip: str) -> dict[str, Any]:
        with self._egress() as client:
            resp = client.get(
                f"{BASE_URL}/network-info/data.json",
                params=self._build_params(ip),
            )
        return self._handle_response(resp, "network-info")

    def abuse_contact_sync(self, resource: str) -> dict[str, Any]:
        with self._egress() as client:
            resp = client.get(
                f"{BASE_URL}/abuse-contact-finder/data.json",
                params=self._build_params(resource),
            )
        return self._handle_response(resp, "abuse-contact-finder")

    def prefix_overview_sync(self, prefix: str) -> dict[str, Any]:
        with self._egress() as client:
            resp = client.get(
                f"{BASE_URL}/prefix-overview/data.json",
                params=self._build_params(prefix),
            )
        return self._handle_response(resp, "prefix-overview")

    def related_prefixes_sync(self, prefix: str) -> dict[str, Any]:
        with self._egress() as client:
            resp = client.get(
                f"{BASE_URL}/related-prefixes/data.json",
                params=self._build_params(prefix),
            )
        return self._handle_response(resp, "related-prefixes")
