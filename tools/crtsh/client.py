from __future__ import annotations

import hashlib

import httpx

from shared.http import get_async_client
from shared.logging import get_logger
from shared.redis import cache_client
from shared.utils.datetime import utc_now
from tools.crtsh.models import CrtShResult
from tools.crtsh.parser import parse_org_search

logger = get_logger(__name__)

BASE_URL = "https://crt.sh"
REQUEST_TIMEOUT = 25.0
CACHE_TTL_SECONDS = 6 * 3600
CACHE_KEY = "crtsh:org:{digest}"


class CrtShError(Exception):
    """crt.sh did not answer or returned something unreadable."""


def _cache_key(organization: str) -> str:
    digest = hashlib.sha256(organization.casefold().encode()).hexdigest()[:32]
    return CACHE_KEY.format(digest=digest)


class CrtShClient:
    async def search_organization(self, organization: str) -> CrtShResult:
        stored = await self._stored(organization)
        if stored is not None:
            return stored
        result = await self._fetch(organization)
        await self._store(organization, result)
        return result

    async def _fetch(self, organization: str) -> CrtShResult:
        params = {"O": organization, "output": "json"}
        try:
            async with get_async_client(
                timeout=httpx.Timeout(REQUEST_TIMEOUT)
            ) as client:
                resp = await client.get(f"{BASE_URL}/", params=params)
        except httpx.TimeoutException:
            msg = f"crt.sh did not answer within {REQUEST_TIMEOUT:.0f} seconds."
            raise CrtShError(msg) from None
        except httpx.HTTPError as exc:
            msg = f"crt.sh could not be reached: {type(exc).__name__}."
            raise CrtShError(msg) from None
        if resp.status_code != httpx.codes.OK:
            msg = f"crt.sh returned HTTP {resp.status_code}."
            raise CrtShError(msg)
        result = parse_org_search(resp.text)
        if result is None:
            msg = "crt.sh returned an unreadable answer."
            raise CrtShError(msg)
        return result

    async def _stored(self, organization: str) -> CrtShResult | None:
        try:
            raw = await cache_client().get(_cache_key(organization))
            return CrtShResult.model_validate_json(raw) if raw else None
        except Exception as exc:
            logger.debug("crt.sh cache read failed", error=type(exc).__name__)
            return None

    async def _store(self, organization: str, result: CrtShResult) -> None:
        stamped = result.model_copy(update={"stored_at": utc_now()})
        try:
            await cache_client().set(
                _cache_key(organization),
                stamped.model_dump_json(),
                ex=CACHE_TTL_SECONDS,
            )
        except Exception as exc:
            logger.debug("crt.sh cache write failed", error=type(exc).__name__)
