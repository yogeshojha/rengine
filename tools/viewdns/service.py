"""ViewDNS.info lookups with a cached response per query."""

from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from typing import Any

from pydantic import ValidationError
from sqlalchemy import tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from shared.enums.api_key import APIProvider
from shared.logging import get_logger
from shared.models.viewdns import ViewDNSCache
from shared.services.api_key.async_api_key import APIKeyService
from shared.utils.datetime import utc_now
from tools.viewdns.client import (
    ViewDNSAPIError,
    ViewDNSAuthError,
    ViewDNSClient,
    ViewDNSRateLimitError,
)
from tools.viewdns.models import (
    CachedCount,
    CachedCountQuery,
    ReverseIPResponse,
    ReverseNSResponse,
    ReverseWhoisResponse,
    ViewDNSCacheRead,
    ViewDNSLookupType,
    ViewDNSResponse,
)
from tools.viewdns.parser import (
    parse_reverse_ip,
    parse_reverse_ns,
    parse_reverse_whois,
)

logger = get_logger(__name__)

DEFAULT_CACHE_TTL_DAYS = 7


def query_key(lookup_type: ViewDNSLookupType, value: str) -> str:
    value = value.strip()
    return value if lookup_type == ViewDNSLookupType.REVERSE_WHOIS else value.lower()


def domains_of(response: ViewDNSResponse) -> list[str]:
    match response:
        case ReverseWhoisResponse():
            return [m.domain for m in response.matches if m.domain]
        case ReverseIPResponse():
            return [d.name for d in response.domains if d.name]
        case ReverseNSResponse():
            return [d.domain for d in response.domains if d.domain]
    return []


class ViewDNSError(Exception):
    """Base exception for ViewDNS service errors."""


class ViewDNSKeyNotConfiguredError(ViewDNSError):
    """API key not configured or disabled."""


class ViewDNSLookupError(ViewDNSError):
    """Lookup failed."""


class ViewDNSService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._api_key_service = APIKeyService(session)

    def _is_fresh(self, record: ViewDNSCache) -> bool:
        if not record.queried_at:
            return False
        return (utc_now() - record.queried_at) < timedelta(days=DEFAULT_CACHE_TTL_DAYS)

    def _reconstruct_response(
        self, lookup_type: ViewDNSLookupType, data: dict
    ) -> ViewDNSResponse:
        match lookup_type:
            case ViewDNSLookupType.REVERSE_IP:
                return ReverseIPResponse.model_validate(data)
            case ViewDNSLookupType.REVERSE_NS:
                return ReverseNSResponse.model_validate(data)
            case ViewDNSLookupType.REVERSE_WHOIS:
                return ReverseWhoisResponse.model_validate(data)
            case _:
                msg = f"Unknown lookup type: {lookup_type}"
                raise ViewDNSLookupError(msg)

    def _to_read(
        self,
        lookup_type: ViewDNSLookupType,
        query_value: str,
        response: ViewDNSResponse,
        result_count: int,
        cached: bool = False,
        queried_at=None,
    ) -> ViewDNSCacheRead:
        return ViewDNSCacheRead(
            lookup_type=lookup_type,
            query_value=query_value,
            result_count=result_count,
            cached=cached,
            queried_at=queried_at,
            data=response,
        )

    async def _get_client(self) -> ViewDNSClient:
        key = await self._api_key_service.get_key_for_provider(APIProvider.VIEWDNS)
        if not key:
            msg = "No active ViewDNS.info API key. Add one in Settings under API keys."
            raise ViewDNSKeyNotConfiguredError(msg)
        return ViewDNSClient(key)

    async def _handle_api_error(self, e: ViewDNSAPIError) -> None:
        if isinstance(e, ViewDNSRateLimitError):
            logger.warning("ViewDNS rate limit: %s", e)
            return
        if isinstance(e, ViewDNSAuthError):
            logger.warning("ViewDNS auth error, disabling key: %s", e)
            await self._api_key_service.disable_key(APIProvider.VIEWDNS)

    async def _get_cached(
        self, lookup_type: ViewDNSLookupType, query_value: str
    ) -> ViewDNSCache | None:
        result = await self._session.execute(
            select(ViewDNSCache).where(
                ViewDNSCache.lookup_type == lookup_type.value,
                ViewDNSCache.query_value == query_value,
            )
        )
        return result.scalar_one_or_none()

    async def _store_cache(
        self,
        lookup_type: ViewDNSLookupType,
        query_value: str,
        response: ViewDNSResponse,
        result_count: int,
    ) -> datetime:
        now = utc_now()
        stmt = insert(ViewDNSCache).values(
            lookup_type=lookup_type.value,
            query_value=query_value,
            response_data=response.model_dump(mode="json"),
            result_count=result_count,
            queried_at=now,
            updated_at=now,
        )
        await self._session.execute(
            stmt.on_conflict_do_update(
                constraint="uq_viewdns_cache_lookup",
                set_={
                    "response_data": stmt.excluded.response_data,
                    "result_count": stmt.excluded.result_count,
                    "queried_at": stmt.excluded.queried_at,
                    "updated_at": stmt.excluded.updated_at,
                },
            )
        )
        await self._session.commit()
        return now

    async def _lookup(
        self,
        lookup_type: ViewDNSLookupType,
        value: str,
        fetch: Callable[[ViewDNSClient, str], Awaitable[dict[str, Any]]],
        parse: Callable[[dict[str, Any], str], ViewDNSResponse],
        count: Callable[[Any], int],
        cached_only: bool,
    ) -> ViewDNSCacheRead | None:
        cached = await self._get_cached(lookup_type, value)
        response = None
        if cached and self._is_fresh(cached):
            try:
                response = self._reconstruct_response(lookup_type, cached.response_data)
            except ValidationError:
                logger.warning("ViewDNS cache row unreadable", lookup=lookup_type.value)
        if cached and response is not None:
            return self._to_read(
                lookup_type,
                value,
                response,
                cached.result_count,
                cached=True,
                queried_at=cached.queried_at,
            )

        if cached_only:
            return None

        client = await self._get_client()
        try:
            raw = await fetch(client, value)
        except ViewDNSAPIError as e:
            await self._handle_api_error(e)
            raise ViewDNSLookupError(str(e)) from e
        response = parse(raw, value)
        result_count = count(response)
        queried_at = await self._store_cache(lookup_type, value, response, result_count)
        return self._to_read(
            lookup_type, value, response, result_count, queried_at=queried_at
        )

    async def reverse_ip(
        self, host: str, cached_only: bool = False
    ) -> ViewDNSCacheRead | None:
        return await self._lookup(
            ViewDNSLookupType.REVERSE_IP,
            query_key(ViewDNSLookupType.REVERSE_IP, host),
            ViewDNSClient.reverse_ip,
            parse_reverse_ip,
            lambda response: response.domain_count,
            cached_only,
        )

    async def reverse_ns(
        self, nameserver: str, cached_only: bool = False
    ) -> ViewDNSCacheRead | None:
        return await self._lookup(
            ViewDNSLookupType.REVERSE_NS,
            query_key(ViewDNSLookupType.REVERSE_NS, nameserver),
            ViewDNSClient.reverse_ns,
            parse_reverse_ns,
            lambda response: response.domain_count,
            cached_only,
        )

    async def reverse_whois(
        self, query: str, cached_only: bool = False
    ) -> ViewDNSCacheRead | None:
        return await self._lookup(
            ViewDNSLookupType.REVERSE_WHOIS,
            query_key(ViewDNSLookupType.REVERSE_WHOIS, query),
            ViewDNSClient.reverse_whois,
            parse_reverse_whois,
            lambda response: response.result_count,
            cached_only,
        )

    async def cached_counts(self, queries: list[CachedCountQuery]) -> list[CachedCount]:
        """Count each lookup's cached domains."""
        keys = {(q.source.value, query_key(q.source, q.query)) for q in queries}
        domains: dict[tuple[str, str], list[str]] = {}
        if keys:
            rows = await self._session.execute(
                select(ViewDNSCache).where(
                    tuple_(ViewDNSCache.lookup_type, ViewDNSCache.query_value).in_(
                        list(keys)
                    )
                )
            )
            for record in rows.scalars():
                if not self._is_fresh(record):
                    continue
                try:
                    response = self._reconstruct_response(
                        ViewDNSLookupType(record.lookup_type), record.response_data
                    )
                except (ValueError, ViewDNSLookupError):
                    continue
                domains[(record.lookup_type, record.query_value)] = [
                    d.lower() for d in domains_of(response)
                ]
        out = []
        for q in queries:
            found = domains.get((q.source.value, query_key(q.source, q.query)))
            own = q.exclude.strip().lower()
            count = None if found is None else sum(1 for d in found if d != own)
            out.append(CachedCount(source=q.source, query=q.query, count=count))
        return out
