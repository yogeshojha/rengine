"""RIPEstat HTTP client.

respect the limits of the api, need to warn user or think later

All endpoints follow the same pattern:
    GET https://stat.ripe.net/data/{endpoint}/data.json?resource=X&sourceapp=rengine

make users signup for sourceapp as its user's responsibility to respect the limits of the api, need to warn user or think later
"""

import os
from typing import Any

import httpx

from shared.http import get_async_client, get_sync_client
from shared.logging import get_logger

logger = get_logger(__name__)

BASE_URL = "https://stat.ripe.net/data"
DEFAULT_SOURCE_APP = "rengine"


class RIPEStatAPIError(Exception):
    """Base error for RIPEstat API calls."""


class RIPEStatRateLimitError(RIPEStatAPIError):
    """Rate limit exceeded (429 or data-level throttle)."""


class RIPEStatClient:
    """Low-level HTTP client for RIPEstat API."""

    def __init__(self, source_app: str | None = None) -> None:
        self._source_app = source_app or os.environ.get(
            "RIPESTAT_SOURCE_APP", DEFAULT_SOURCE_APP
        )

    def _build_params(self, resource: str, **kwargs) -> dict[str, str]:
        params = {
            "resource": resource,
            "sourceapp": self._source_app,
        }
        params.update({k: v for k, v in kwargs.items() if v is not None})
        return params

    def _handle_response(self, resp: httpx.Response, endpoint: str) -> dict[str, Any]:
        if resp.status_code == 429:  # noqa: PLR2004
            msg = f"RIPEstat rate limit on {endpoint}"
            raise RIPEStatRateLimitError(msg)
        resp.raise_for_status()

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

    async def announced_prefixes(self, asn: str) -> dict[str, Any]:
        async with get_async_client() as client:
            resp = await client.get(
                f"{BASE_URL}/announced-prefixes/data.json",
                params=self._build_params(asn),
            )
        return self._handle_response(resp, "announced-prefixes")

    async def asn_neighbours(self, asn: str) -> dict[str, Any]:
        async with get_async_client() as client:
            resp = await client.get(
                f"{BASE_URL}/asn-neighbours/data.json",
                params=self._build_params(asn),
            )
        return self._handle_response(resp, "asn-neighbours")

    async def as_overview(self, asn: str) -> dict[str, Any]:
        async with get_async_client() as client:
            resp = await client.get(
                f"{BASE_URL}/as-overview/data.json",
                params=self._build_params(asn),
            )
        return self._handle_response(resp, "as-overview")

    async def network_info(self, ip: str) -> dict[str, Any]:
        async with get_async_client() as client:
            resp = await client.get(
                f"{BASE_URL}/network-info/data.json",
                params=self._build_params(ip),
            )
        return self._handle_response(resp, "network-info")

    async def abuse_contact(self, resource: str) -> dict[str, Any]:
        async with get_async_client() as client:
            resp = await client.get(
                f"{BASE_URL}/abuse-contact-finder/data.json",
                params=self._build_params(resource),
            )
        return self._handle_response(resp, "abuse-contact-finder")

    async def prefix_overview(self, prefix: str) -> dict[str, Any]:
        async with get_async_client() as client:
            resp = await client.get(
                f"{BASE_URL}/prefix-overview/data.json",
                params=self._build_params(prefix),
            )
        return self._handle_response(resp, "prefix-overview")

    async def related_prefixes(self, prefix: str) -> dict[str, Any]:
        async with get_async_client() as client:
            resp = await client.get(
                f"{BASE_URL}/related-prefixes/data.json",
                params=self._build_params(prefix),
            )
        return self._handle_response(resp, "related-prefixes")

    # celery sync methods

    def announced_prefixes_sync(self, asn: str) -> dict[str, Any]:
        with get_sync_client() as client:
            resp = client.get(
                f"{BASE_URL}/announced-prefixes/data.json",
                params=self._build_params(asn),
            )
        return self._handle_response(resp, "announced-prefixes")

    def asn_neighbours_sync(self, asn: str) -> dict[str, Any]:
        with get_sync_client() as client:
            resp = client.get(
                f"{BASE_URL}/asn-neighbours/data.json",
                params=self._build_params(asn),
            )
        return self._handle_response(resp, "asn-neighbours")

    def as_overview_sync(self, asn: str) -> dict[str, Any]:
        with get_sync_client() as client:
            resp = client.get(
                f"{BASE_URL}/as-overview/data.json",
                params=self._build_params(asn),
            )
        return self._handle_response(resp, "as-overview")

    def network_info_sync(self, ip: str) -> dict[str, Any]:
        with get_sync_client() as client:
            resp = client.get(
                f"{BASE_URL}/network-info/data.json",
                params=self._build_params(ip),
            )
        return self._handle_response(resp, "network-info")

    def abuse_contact_sync(self, resource: str) -> dict[str, Any]:
        with get_sync_client() as client:
            resp = client.get(
                f"{BASE_URL}/abuse-contact-finder/data.json",
                params=self._build_params(resource),
            )
        return self._handle_response(resp, "abuse-contact-finder")

    def prefix_overview_sync(self, prefix: str) -> dict[str, Any]:
        with get_sync_client() as client:
            resp = client.get(
                f"{BASE_URL}/prefix-overview/data.json",
                params=self._build_params(prefix),
            )
        return self._handle_response(resp, "prefix-overview")

    def related_prefixes_sync(self, prefix: str) -> dict[str, Any]:
        with get_sync_client() as client:
            resp = client.get(
                f"{BASE_URL}/related-prefixes/data.json",
                params=self._build_params(prefix),
            )
        return self._handle_response(resp, "related-prefixes")
