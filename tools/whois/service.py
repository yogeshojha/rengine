"""WHOIS lookups — standalone, or persisted and linked to a target for correlation."""

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from shared.enums.target import TargetType
from shared.enums.whois import WhoisLookupType
from shared.logging import get_logger
from shared.models.whois import WhoisNameserver, WhoisRecord
from shared.utils.datetime import normalize_datetime, utc_now
from shared.utils.infra import is_shared_nameserver
from shared.utils.privacy import is_redacted_name
from shared.utils.validation import (
    extract_asn_number,
    normalize_domain,
    normalize_query,
    validate_target,
)
from tools.whois.models import (
    WhoisASNResponse,
    WhoisDomainResponse,
    WhoisIPResponse,
    WhoisResponse,
)
from tools.whois.parser import (
    parse_asn_response,
    parse_domain_response,
    parse_ip_response,
)
from tools.whois.providers.whoisit import RDAPProvider, RDAPProviderError

logger = get_logger(__name__)

DEFAULT_CACHE_TTL_DAYS = 7

# cap rows per correlation group
MAX_CORRELATION_RECORDS = 500


@dataclass(slots=True)
class WhoisLookupResult:
    """Result of an async WHOIS lookup, including cache provenance."""

    response: "WhoisResponse"
    cache_hit: bool


class WhoisError(Exception):
    """Base exception for whois service errors."""


class WhoisValidationError(WhoisError):
    """Raised when input validation fails."""


class WhoisLookupError(WhoisError):
    """Raised when a WHOIS lookup fails."""


class WhoisService:
    """WHOIS lookup service with optional DB caching."""

    def __init__(self, cache_ttl_days: int = DEFAULT_CACHE_TTL_DAYS) -> None:
        self._provider = RDAPProvider()
        self.cache_ttl_days = cache_ttl_days

    # Core lookup (sync, no DB)

    def do_lookup(self, query: str, target_type) -> WhoisResponse:
        match target_type:
            case TargetType.DOMAIN:
                return self.lookup_domain(query)
            case TargetType.IP | TargetType.IP_RANGE:
                return self.lookup_ip(query)
            case TargetType.ASN:
                asn_number = extract_asn_number(query)
                return self.lookup_asn(asn_number, query)
            case TargetType.URL:
                domain = normalize_domain(query)
                return self.lookup_domain(domain)
            case _:
                msg = f"Unsupported target type for WHOIS: {target_type}"
                raise WhoisValidationError(msg)

    def lookup_domain(self, domain: str) -> WhoisResponse:
        domain = normalize_domain(domain)
        try:
            raw = self._provider.lookup_domain(domain)
            return parse_domain_response(raw, domain)
        except RDAPProviderError as e:
            raise WhoisLookupError(str(e)) from e

    def lookup_ip(self, ip: str) -> WhoisResponse:
        ip = ip.strip()
        try:
            raw = self._provider.lookup_ip(ip)
            return parse_ip_response(raw, ip)
        except RDAPProviderError as e:
            raise WhoisLookupError(str(e)) from e

    def lookup_asn(self, asn: int, original_query: str = "") -> WhoisResponse:
        query_str = original_query or str(asn)
        try:
            raw = self._provider.lookup_asn(asn)
            return parse_asn_response(raw, query_str)
        except RDAPProviderError as e:
            raise WhoisLookupError(str(e)) from e

    # Async DB operations (API context)
    async def lookup(
        self,
        query: str,
        target_type=None,
        store_in_db: bool = True,
        session: AsyncSession | None = None,
    ) -> WhoisLookupResult:
        """Async WHOIS lookup with optional DB caching."""
        if not query or not query.strip():
            msg = "Query cannot be empty"
            raise WhoisValidationError(msg)

        query = query.strip()

        if target_type is None:
            target_type = self._detect_type(query)

        normalized = normalize_query(query, target_type)

        if store_in_db and session:
            cached = await self._get_cached_record(session, normalized)
            if cached and self._is_cache_fresh(cached):
                logger.debug(f"WHOIS cache hit for {normalized}")
                return WhoisLookupResult(
                    response=self._reconstruct_response(cached),
                    cache_hit=True,
                )

        # whoisit/requests is synchronous blocking I/O - offload off the loop
        response = await asyncio.to_thread(self.do_lookup, normalized, target_type)

        if store_in_db and session:
            await self._store_record(session, response, normalized)

        return WhoisLookupResult(response=response, cache_hit=False)

    async def _get_cached_record(
        self, session: AsyncSession, query_value: str
    ) -> WhoisRecord | None:
        result = await session.execute(
            select(WhoisRecord).where(WhoisRecord.query_value == query_value)
        )
        return result.scalar_one_or_none()

    async def _store_record(
        self,
        session: AsyncSession,
        response: WhoisResponse,
        query_value: str,
    ) -> WhoisRecord:
        """Store or update a WHOIS record."""
        existing = await self._get_cached_record(session, query_value)
        db_fields = self._prepare_db_fields(response)
        now = utc_now()

        if existing:
            for key, value in db_fields.items():
                setattr(existing, key, value)
            existing.queried_at = now
            existing.updated_at = now
            await session.flush()
            await self._sync_nameservers(
                session, existing.id, db_fields.get("nameservers")
            )
            await session.commit()
            return existing

        record = WhoisRecord(**db_fields, queried_at=now)
        session.add(record)
        try:
            await session.flush()
            await self._sync_nameservers(
                session, record.id, db_fields.get("nameservers")
            )
            await session.commit()
            return record
        except IntegrityError:
            # concurrent insert for the same query_value won the race; update it
            await session.rollback()
            existing = await self._get_cached_record(session, query_value)
            if existing is None:
                raise
            for key, value in db_fields.items():
                setattr(existing, key, value)
            existing.queried_at = now
            existing.updated_at = now
            await session.flush()
            await self._sync_nameservers(
                session, existing.id, db_fields.get("nameservers")
            )
            await session.commit()
            return existing

    # Sync DB operations (Celery worker context)

    def get_cached_record_sync(
        self, session: Session, query_value: str
    ) -> WhoisRecord | None:
        """Get cached WHOIS record (sync)."""
        result = session.execute(
            select(WhoisRecord).where(WhoisRecord.query_value == query_value)
        )
        return result.scalar_one_or_none()

    def store_record_sync(
        self, session: Session, response: WhoisResponse
    ) -> WhoisRecord:
        """Store or update a WHOIS record (sync)."""
        db_fields = self._prepare_db_fields(response)
        now = utc_now()

        existing = self.get_cached_record_sync(session, db_fields["query_value"])

        if existing:
            for key, value in db_fields.items():
                setattr(existing, key, value)
            existing.queried_at = now
            existing.updated_at = now
            session.flush()
            self._sync_nameservers_sync(
                session, existing.id, db_fields.get("nameservers")
            )
            session.commit()
            return existing

        record = WhoisRecord(**db_fields, queried_at=now)
        session.add(record)
        session.flush()
        self._sync_nameservers_sync(session, record.id, db_fields.get("nameservers"))
        session.commit()
        session.refresh(record)
        return record

    def get_or_create_record_sync(
        self, session: Session, normalized_query: str, target_type
    ) -> WhoisRecord:
        """Get cached record or perform lookup and store (sync)."""
        existing = self.get_cached_record_sync(session, normalized_query)
        if existing:
            return existing

        response = self.do_lookup(normalized_query, target_type)
        return self.store_record_sync(session, response)

    # Shared helpers

    def _prepare_db_fields(self, response: WhoisResponse) -> dict:
        """Prepare response fields for DB storage."""
        db_fields = response.to_db_fields()
        for key, value in db_fields.items():
            if isinstance(value, datetime):
                db_fields[key] = normalize_datetime(value)
        return db_fields

    def _is_cache_fresh(self, record: WhoisRecord) -> bool:
        if not record.queried_at:
            return False
        age = utc_now() - record.queried_at
        return age < timedelta(days=self.cache_ttl_days)

    async def _sync_nameservers(
        self,
        session: AsyncSession,
        record_id: uuid.UUID,
        nameservers: list[str] | None,
    ) -> None:
        """Replace nameserver rows for a WHOIS record."""
        await session.execute(
            delete(WhoisNameserver).where(WhoisNameserver.whois_record_id == record_id)
        )
        for ns in nameservers or []:
            _ns = ns.strip().lower()
            if _ns:
                session.add(WhoisNameserver(whois_record_id=record_id, nameserver=_ns))

    def _sync_nameservers_sync(
        self,
        session: Session,
        record_id: uuid.UUID,
        nameservers: list[str] | None,
    ) -> None:
        """Replace nameserver rows for a WHOIS record (sync)."""
        session.execute(
            delete(WhoisNameserver).where(WhoisNameserver.whois_record_id == record_id)
        )
        for ns in nameservers or []:
            _ns = ns.strip().lower()
            if _ns:
                session.add(WhoisNameserver(whois_record_id=record_id, nameserver=_ns))

    def _reconstruct_response(self, record: WhoisRecord) -> WhoisResponse:
        data = record.parsed_data
        if not data:
            msg = f"No parsed data stored for record {record.id}"
            raise WhoisLookupError(msg)

        match record.lookup_type:
            case WhoisLookupType.DOMAIN:
                return WhoisDomainResponse.model_validate(data)
            case WhoisLookupType.IP:
                return WhoisIPResponse.model_validate(data)
            case WhoisLookupType.ASN:
                return WhoisASNResponse.model_validate(data)
            case _:
                msg = f"Unknown lookup type: {record.lookup_type}"
                raise WhoisLookupError(msg)

    def _detect_type(self, query: str):
        """Detect the target type from a query string."""
        target_type = validate_target(query)
        if not target_type:
            msg = f"Cannot determine WHOIS lookup type for: {query}"
            raise WhoisValidationError(msg)
        return target_type

    # Correlation queries

    async def find_by_registrant(
        self,
        session: AsyncSession,
        registrant_name: str,
        limit: int = MAX_CORRELATION_RECORDS,
    ) -> list[WhoisRecord]:
        if is_redacted_name(registrant_name):
            return []
        result = await session.execute(
            select(WhoisRecord)
            .where(WhoisRecord.registrant_name == registrant_name)
            .where(WhoisRecord.registrant_name != "")
            .limit(limit)
        )
        return list(result.scalars().all())

    async def find_by_registrar(
        self,
        session: AsyncSession,
        registrar_name: str,
        limit: int = MAX_CORRELATION_RECORDS,
    ) -> list[WhoisRecord]:
        result = await session.execute(
            select(WhoisRecord)
            .where(WhoisRecord.registrar_name == registrar_name)
            .where(WhoisRecord.registrar_name != "")
            .limit(limit)
        )
        return list(result.scalars().all())

    async def find_by_network(
        self,
        session: AsyncSession,
        network_cidr: str,
        limit: int = MAX_CORRELATION_RECORDS,
    ) -> list[WhoisRecord]:
        result = await session.execute(
            select(WhoisRecord)
            .where(WhoisRecord.network_cidr == network_cidr)
            .where(WhoisRecord.network_cidr != "")
            .limit(limit)
        )
        return list(result.scalars().all())

    async def find_by_country(
        self,
        session: AsyncSession,
        country: str,
        limit: int = MAX_CORRELATION_RECORDS,
    ) -> list[WhoisRecord]:
        result = await session.execute(
            select(WhoisRecord)
            .where(WhoisRecord.country == country.upper())
            .where(WhoisRecord.country != "")
            .limit(limit)
        )
        return list(result.scalars().all())

    async def find_by_nameserver(
        self,
        session: AsyncSession,
        nameserver: str,
        limit: int = MAX_CORRELATION_RECORDS,
    ) -> list[WhoisRecord]:
        result = await session.execute(
            select(WhoisRecord)
            .join(WhoisNameserver, WhoisNameserver.whois_record_id == WhoisRecord.id)
            .where(WhoisNameserver.nameserver == nameserver.strip().lower())
            .distinct()
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_correlations_for_target(
        self, session: AsyncSession, whois_record_id: uuid.UUID
    ) -> dict[str, list[WhoisRecord]]:
        """Correlation groups for a record (excludes country and redacted/shared keys)."""
        result = await session.execute(
            select(WhoisRecord).where(WhoisRecord.id == whois_record_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            return {}

        correlations: dict[str, list[WhoisRecord]] = {}

        # skip redacted registrant placeholders
        if record.registrant_name and not is_redacted_name(record.registrant_name):
            related = await self.find_by_registrant(session, record.registrant_name)
            others = [r for r in related if r.id != record.id]
            if others:
                correlations["registrant_name"] = others

        if record.registrar_name:
            related = await self.find_by_registrar(session, record.registrar_name)
            others = [r for r in related if r.id != record.id]
            if others:
                correlations["registrar_name"] = others

        if record.network_cidr:
            related = await self.find_by_network(session, record.network_cidr)
            others = [r for r in related if r.id != record.id]
            if others:
                correlations["network_cidr"] = others

        ns_related = await self._find_nameserver_correlations(session, record)
        if ns_related:
            correlations["nameserver"] = ns_related

        return correlations

    async def _find_nameserver_correlations(
        self, session: AsyncSession, record: WhoisRecord
    ) -> list[WhoisRecord]:
        """Other records sharing a non-shared nameserver with record."""
        correlatable = [
            ns.strip().lower()
            for ns in (record.nameservers or [])
            if ns and not is_shared_nameserver(ns)
        ]
        if not correlatable:
            return []

        result = await session.execute(
            select(WhoisRecord)
            .join(WhoisNameserver, WhoisNameserver.whois_record_id == WhoisRecord.id)
            .where(WhoisNameserver.nameserver.in_(correlatable))
            .where(WhoisRecord.id != record.id)
            .distinct()
            .limit(MAX_CORRELATION_RECORDS)
        )
        return list(result.scalars().all())

    def ensure_ready(self) -> None:
        try:
            self._provider.ensure_bootstrapped()
        except RDAPProviderError as e:
            msg = f"Failed to initialize WHOIS service: {e}"
            raise WhoisLookupError(msg) from e

    def refresh_bootstrap(self, max_age_days: int = 3) -> None:
        try:
            self._provider.refresh_if_stale(max_age_days)
        except RDAPProviderError as e:
            logger.warning(f"Failed to refresh bootstrap data: {e}")

    def save_bootstrap(self) -> str | None:
        return self._provider.save_bootstrap_data()

    def load_bootstrap(self, data: str) -> None:
        try:
            self._provider.load_bootstrap_data(data)
        except RDAPProviderError as e:
            msg = f"Failed to load bootstrap data: {e}"
            raise WhoisLookupError(msg) from e
