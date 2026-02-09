"""ViewDNS service — main interface for all ViewDNS.info lookups."""

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlmodel import select

from shared.enums.api_key import APIProvider
from shared.logging import get_logger
from shared.models.viewdns import ViewDNSCache
from shared.services.api_key.async_api_key import APIKeyService
from shared.services.api_key.sync_api_key import SyncAPIKeyService
from shared.utils.datetime import utc_now
from tools.viewdns.client import (
    ViewDNSAPIError,
    ViewDNSAuthError,
    ViewDNSClient,
    ViewDNSRateLimitError,
)
from tools.viewdns.models import (
    IPHistoryResponse,
    ReverseIPResponse,
    ReverseNSResponse,
    ReverseWhoisResponse,
    ViewDNSCacheRead,
    ViewDNSLookupType,
    ViewDNSResponse,
)
from tools.viewdns.parser import (
    parse_ip_history,
    parse_reverse_ip,
    parse_reverse_ns,
    parse_reverse_whois,
)

logger = get_logger("tools.viewdns.service")

DEFAULT_CACHE_TTL_DAYS = 7


class ViewDNSError(Exception):
    """Base exception for ViewDNS service errors."""


class ViewDNSKeyNotConfiguredError(ViewDNSError):
    """API key not configured or disabled."""


class ViewDNSLookupError(ViewDNSError):
    """Lookup failed."""


class ViewDNSService:
    def __init__(
        self,
        session: AsyncSession | None = None,
        cache_ttl_days: int = DEFAULT_CACHE_TTL_DAYS,
    ) -> None:
        self._session = session
        self._api_key_service = APIKeyService(session) if session else None
        self.cache_ttl_days = cache_ttl_days

    def _is_fresh(self, record: ViewDNSCache) -> bool:
        if not record.queried_at:
            return False
        return (utc_now() - record.queried_at) < timedelta(days=self.cache_ttl_days)

    def _reconstruct_response(
        self, lookup_type: ViewDNSLookupType, data: dict
    ) -> ViewDNSResponse:
        match lookup_type:
            case ViewDNSLookupType.IP_HISTORY:
                return IPHistoryResponse.model_validate(data)
            case ViewDNSLookupType.REVERSE_IP:
                return ReverseIPResponse.model_validate(data)
            case ViewDNSLookupType.REVERSE_NS:
                return ReverseNSResponse.model_validate(data)
            case ViewDNSLookupType.REVERSE_WHOIS:
                return ReverseWhoisResponse.model_validate(data)

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
            msg = (
                "ViewDNS.info API key is not configured or is disabled. "
                "Add one in Settings -> API Keys or via API."
            )
            raise ViewDNSKeyNotConfiguredError(msg)
        return ViewDNSClient(key)

    async def _post_success(self) -> None:
        await self._api_key_service.increment_usage(APIProvider.VIEWDNS)

    async def _handle_api_error(self, e: ViewDNSAPIError) -> None:
        if isinstance(e, (ViewDNSRateLimitError, ViewDNSAuthError)):
            label = (
                "rate limit" if isinstance(e, ViewDNSRateLimitError) else "auth error"
            )
            logger.warning("ViewDNS %s, disabling key: %s", label, e)
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
    ) -> ViewDNSCache:
        now = utc_now()
        existing = await self._get_cached(lookup_type, query_value)

        if existing:
            existing.response_data = response.model_dump(mode="json")
            existing.result_count = result_count
            existing.queried_at = now
            existing.updated_at = now
            self._session.add(existing)
            await self._session.commit()
            return existing

        record = ViewDNSCache(
            lookup_type=lookup_type.value,
            query_value=query_value,
            response_data=response.model_dump(mode="json"),
            result_count=result_count,
            queried_at=now,
        )
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        return record

    def _get_client_sync(self, session: Session) -> ViewDNSClient:
        api_key_service = SyncAPIKeyService(session)
        key = api_key_service.get_key_for_provider(APIProvider.VIEWDNS)
        if not key:
            msg = (
                "ViewDNS.info API key is not configured or is disabled. "
                "Add one in Settings -> API Keys or via API."
            )
            raise ViewDNSKeyNotConfiguredError(msg)
        return ViewDNSClient(key)

    def _post_success_sync(self, session: Session) -> None:
        api_key_service = SyncAPIKeyService(session)
        api_key_service.increment_usage(APIProvider.VIEWDNS)

    def _handle_api_error_sync(self, session: Session, e: ViewDNSAPIError) -> None:
        if isinstance(e, (ViewDNSRateLimitError, ViewDNSAuthError)):
            label = (
                "rate limit" if isinstance(e, ViewDNSRateLimitError) else "auth error"
            )
            logger.warning("ViewDNS %s, disabling key: %s", label, e)
            api_key_service = SyncAPIKeyService(session)
            api_key_service.disable_key(APIProvider.VIEWDNS)

    def _get_cached_sync(
        self, session: Session, lookup_type: ViewDNSLookupType, query_value: str
    ) -> ViewDNSCache | None:
        result = session.execute(
            select(ViewDNSCache).where(
                ViewDNSCache.lookup_type == lookup_type.value,
                ViewDNSCache.query_value == query_value,
            )
        )
        return result.scalar_one_or_none()

    def _store_cache_sync(
        self,
        session: Session,
        lookup_type: ViewDNSLookupType,
        query_value: str,
        response: ViewDNSResponse,
        result_count: int,
    ) -> ViewDNSCache:
        now = utc_now()
        existing = self._get_cached_sync(session, lookup_type, query_value)

        if existing:
            existing.response_data = response.model_dump(mode="json")
            existing.result_count = result_count
            existing.queried_at = now
            existing.updated_at = now
            session.add(existing)
            session.commit()
            return existing

        record = ViewDNSCache(
            lookup_type=lookup_type.value,
            query_value=query_value,
            response_data=response.model_dump(mode="json"),
            result_count=result_count,
            queried_at=now,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return record

    # async for fasapi methods

    async def ip_history(
        self, domain: str, cached_only: bool = False
    ) -> ViewDNSCacheRead | None:
        domain = domain.strip().lower()
        lookup_type = ViewDNSLookupType.IP_HISTORY

        cached = await self._get_cached(lookup_type, domain)
        if cached and self._is_fresh(cached):
            logger.debug("ViewDNS cache hit: ip_history for %s", domain)
            response = self._reconstruct_response(lookup_type, cached.response_data)
            return self._to_read(
                lookup_type,
                domain,
                response,
                cached.result_count,
                cached=True,
                queried_at=cached.queried_at,
            )

        if cached_only:
            return None

        client = await self._get_client()
        try:
            raw = await client.ip_history(domain)
            response = parse_ip_history(raw, domain)
            result_count = len(response.records)
            await self._post_success()
            record = await self._store_cache(
                lookup_type, domain, response, result_count
            )
            return self._to_read(
                lookup_type,
                domain,
                response,
                result_count,
                queried_at=record.queried_at,
            )
        except ViewDNSAPIError as e:
            await self._handle_api_error(e)
            raise ViewDNSLookupError(str(e)) from e

    async def reverse_ip(
        self, host: str, cached_only: bool = False
    ) -> ViewDNSCacheRead | None:
        host = host.strip().lower()
        lookup_type = ViewDNSLookupType.REVERSE_IP

        cached = await self._get_cached(lookup_type, host)
        if cached and self._is_fresh(cached):
            logger.debug("ViewDNS cache hit: reverse_ip for %s", host)
            response = self._reconstruct_response(lookup_type, cached.response_data)
            return self._to_read(
                lookup_type,
                host,
                response,
                cached.result_count,
                cached=True,
                queried_at=cached.queried_at,
            )

        if cached_only:
            return None

        client = await self._get_client()
        try:
            raw = await client.reverse_ip(host)
            response = parse_reverse_ip(raw, host)
            result_count = response.domain_count
            await self._post_success()
            record = await self._store_cache(lookup_type, host, response, result_count)
            return self._to_read(
                lookup_type,
                host,
                response,
                result_count,
                queried_at=record.queried_at,
            )
        except ViewDNSAPIError as e:
            await self._handle_api_error(e)
            raise ViewDNSLookupError(str(e)) from e

    async def reverse_ns(
        self, nameserver: str, cached_only: bool = False
    ) -> ViewDNSCacheRead | None:
        nameserver = nameserver.strip().lower()
        lookup_type = ViewDNSLookupType.REVERSE_NS

        cached = await self._get_cached(lookup_type, nameserver)
        if cached and self._is_fresh(cached):
            logger.debug("ViewDNS cache hit: reverse_ns for %s", nameserver)
            response = self._reconstruct_response(lookup_type, cached.response_data)
            return self._to_read(
                lookup_type,
                nameserver,
                response,
                cached.result_count,
                cached=True,
                queried_at=cached.queried_at,
            )

        if cached_only:
            return None

        client = await self._get_client()
        try:
            raw = await client.reverse_ns(nameserver)
            response = parse_reverse_ns(raw, nameserver)
            result_count = response.domain_count
            await self._post_success()
            record = await self._store_cache(
                lookup_type, nameserver, response, result_count
            )
            return self._to_read(
                lookup_type,
                nameserver,
                response,
                result_count,
                queried_at=record.queried_at,
            )
        except ViewDNSAPIError as e:
            await self._handle_api_error(e)
            raise ViewDNSLookupError(str(e)) from e

    async def reverse_whois(
        self, query: str, cached_only: bool = False
    ) -> ViewDNSCacheRead | None:
        query = query.strip()
        lookup_type = ViewDNSLookupType.REVERSE_WHOIS

        cached = await self._get_cached(lookup_type, query)
        if cached and self._is_fresh(cached):
            logger.debug("ViewDNS cache hit: reverse_whois for %s", query)
            response = self._reconstruct_response(lookup_type, cached.response_data)
            return self._to_read(
                lookup_type,
                query,
                response,
                cached.result_count,
                cached=True,
                queried_at=cached.queried_at,
            )

        if cached_only:
            return None

        client = await self._get_client()
        try:
            raw = await client.reverse_whois(query)
            response = parse_reverse_whois(raw, query)
            result_count = response.result_count
            await self._post_success()
            record = await self._store_cache(lookup_type, query, response, result_count)
            return self._to_read(
                lookup_type,
                query,
                response,
                result_count,
                queried_at=record.queried_at,
            )
        except ViewDNSAPIError as e:
            await self._handle_api_error(e)
            raise ViewDNSLookupError(str(e)) from e

    # sync methods for celery tasks

    def ip_history_sync(
        self, session: Session, domain: str, cached_only: bool = False
    ) -> ViewDNSCacheRead | None:
        domain = domain.strip().lower()
        lookup_type = ViewDNSLookupType.IP_HISTORY

        cached = self._get_cached_sync(session, lookup_type, domain)
        if cached and self._is_fresh(cached):
            logger.debug("ViewDNS cache hit: ip_history for %s", domain)
            response = self._reconstruct_response(lookup_type, cached.response_data)
            return self._to_read(
                lookup_type,
                domain,
                response,
                cached.result_count,
                cached=True,
                queried_at=cached.queried_at,
            )

        if cached_only:
            return None

        client = self._get_client_sync(session)
        try:
            raw = client.ip_history_sync(domain)
            response = parse_ip_history(raw, domain)
            result_count = len(response.records)
            self._post_success_sync(session)
            record = self._store_cache_sync(
                session, lookup_type, domain, response, result_count
            )
            return self._to_read(
                lookup_type,
                domain,
                response,
                result_count,
                queried_at=record.queried_at,
            )
        except ViewDNSAPIError as e:
            self._handle_api_error_sync(session, e)
            raise ViewDNSLookupError(str(e)) from e

    def reverse_ip_sync(
        self, session: Session, host: str, cached_only: bool = False
    ) -> ViewDNSCacheRead | None:
        host = host.strip().lower()
        lookup_type = ViewDNSLookupType.REVERSE_IP

        cached = self._get_cached_sync(session, lookup_type, host)
        if cached and self._is_fresh(cached):
            logger.debug("ViewDNS cache hit: reverse_ip for %s", host)
            response = self._reconstruct_response(lookup_type, cached.response_data)
            return self._to_read(
                lookup_type,
                host,
                response,
                cached.result_count,
                cached=True,
                queried_at=cached.queried_at,
            )

        if cached_only:
            return None

        client = self._get_client_sync(session)
        try:
            raw = client.reverse_ip_sync(host)
            response = parse_reverse_ip(raw, host)
            result_count = response.domain_count
            self._post_success_sync(session)
            record = self._store_cache_sync(
                session, lookup_type, host, response, result_count
            )
            return self._to_read(
                lookup_type,
                host,
                response,
                result_count,
                queried_at=record.queried_at,
            )
        except ViewDNSAPIError as e:
            self._handle_api_error_sync(session, e)
            raise ViewDNSLookupError(str(e)) from e

    def reverse_ns_sync(
        self, session: Session, nameserver: str, cached_only: bool = False
    ) -> ViewDNSCacheRead | None:
        nameserver = nameserver.strip().lower()
        lookup_type = ViewDNSLookupType.REVERSE_NS

        cached = self._get_cached_sync(session, lookup_type, nameserver)
        if cached and self._is_fresh(cached):
            logger.debug("ViewDNS cache hit: reverse_ns for %s", nameserver)
            response = self._reconstruct_response(lookup_type, cached.response_data)
            return self._to_read(
                lookup_type,
                nameserver,
                response,
                cached.result_count,
                cached=True,
                queried_at=cached.queried_at,
            )

        if cached_only:
            return None

        client = self._get_client_sync(session)
        try:
            raw = client.reverse_ns_sync(nameserver)
            response = parse_reverse_ns(raw, nameserver)
            result_count = response.domain_count
            self._post_success_sync(session)
            record = self._store_cache_sync(
                session, lookup_type, nameserver, response, result_count
            )
            return self._to_read(
                lookup_type,
                nameserver,
                response,
                result_count,
                queried_at=record.queried_at,
            )
        except ViewDNSAPIError as e:
            self._handle_api_error_sync(session, e)
            raise ViewDNSLookupError(str(e)) from e

    def reverse_whois_sync(
        self, session: Session, query: str, cached_only: bool = False
    ) -> ViewDNSCacheRead | None:
        query = query.strip()
        lookup_type = ViewDNSLookupType.REVERSE_WHOIS

        cached = self._get_cached_sync(session, lookup_type, query)
        if cached and self._is_fresh(cached):
            logger.debug("ViewDNS cache hit: reverse_whois for %s", query)
            response = self._reconstruct_response(lookup_type, cached.response_data)
            return self._to_read(
                lookup_type,
                query,
                response,
                cached.result_count,
                cached=True,
                queried_at=cached.queried_at,
            )

        if cached_only:
            return None

        client = self._get_client_sync(session)
        try:
            raw = client.reverse_whois_sync(query)
            response = parse_reverse_whois(raw, query)
            result_count = response.result_count
            self._post_success_sync(session)
            record = self._store_cache_sync(
                session, lookup_type, query, response, result_count
            )
            return self._to_read(
                lookup_type,
                query,
                response,
                result_count,
                queried_at=record.queried_at,
            )
        except ViewDNSAPIError as e:
            self._handle_api_error_sync(session, e)
            raise ViewDNSLookupError(str(e)) from e
