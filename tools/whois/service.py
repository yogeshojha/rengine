"""Whois service - main interface for all sort of WHOIS lookups.

1. Standalone lookup, wont store in db
2. Persistent lookup, will store in db and link to target if target_id provided

The stored records enable correlation queries across all targets:
mostly for Same registrant? Same registrar? Same nameservers?
"""

import re
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.enums.target import TargetType
from shared.logging import get_logger
from shared.models.whois import WhoisRecord
from shared.utils.validation import validate_target
from tools.whois.enums import WhoisLookupType
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

logger = get_logger("tools.whois.service")

DEFAULT_CACHE_TTL_DAYS = 7


class WhoisError(Exception):
    """Base exception for whois service errors."""


class WhoisValidationError(WhoisError):
    """Raised when input validation fails."""


class WhoisLookupError(WhoisError):
    """Raised when a WHOIS lookup fails."""


class WhoisService:
    """WHOIS lookup service with optional DB caching.

    Usage (standalone — no DB):
        service = WhoisService()
        result = service.lookup_domain("example.com")

    Usage (with DB — caching + correlation):
        service = WhoisService()
        result = await service.lookup(
            query="example.com",
            session=db_session,
            target_id=some_target_uuid,
        )
    """

    def __init__(self, cache_ttl_days: int = DEFAULT_CACHE_TTL_DAYS) -> None:
        self._provider = RDAPProvider()
        self.cache_ttl_days = cache_ttl_days

    async def lookup(
        self,
        query: str,
        target_type: TargetType | None = None,
        target_id: uuid.UUID | None = None,
        store_in_db: bool = True,
        session: AsyncSession | None = None,
    ) -> WhoisResponse:
        """whois lookup with optional DB caching.

        1. If session provided and store_in_db, check DB cache
        2. If fresh cached record exists, return it
        3. Otherwise query RDAP, parse response
        4. Store/update in DB if session provided
        5. Return parsed response

        Args:
            query: The value to look up (domain, IP, CIDR, ASN, URL).
            target_type: Optional explicit target type (auto-detected if None).
            target_id: Link record to this target (for enrichment after creation).
            store_in_db: Whether to persist the result (default True).
            session: AsyncSession for DB operations. Required for caching.

        Returns:
            Typed WhoisResponse (domain, IP, or ASN variant).
        """
        if not query or not query.strip():
            msg = "Query cannot be empty"
            raise WhoisValidationError(msg)

        query = query.strip()

        if target_type is None:
            target_type = self._detect_type(query)

        normalized = self._normalize_query(query, target_type)

        if store_in_db and session:
            cached = await self._get_cached_record(session, normalized)
            if cached:
                if target_id and not cached.target_id:
                    cached.target_id = target_id
                    cached.updated_at = datetime.now(UTC).replace(tzinfo=None)
                    await session.commit()

                if self._is_cache_fresh(cached):
                    logger.debug(f"WHOIS cache hit for {normalized}")
                    return self._reconstruct_response(cached)

        response = self._do_lookup(normalized, target_type)

        if store_in_db and session:
            await self._store_record(session, response, target_id, normalized)

        return response

    def lookup_domain(self, domain: str) -> WhoisResponse:
        domain = self._normalize_domain(domain)
        self._validate_domain(domain)
        try:
            raw = self._provider.lookup_domain(domain)
            return parse_domain_response(raw, domain)
        except RDAPProviderError as e:
            raise WhoisLookupError(str(e)) from e

    def lookup_ip(self, ip: str) -> WhoisResponse:
        ip = ip.strip()
        self._validate_ip(ip)
        try:
            raw = self._provider.lookup_ip(ip)
            return parse_ip_response(raw, ip)
        except RDAPProviderError as e:
            raise WhoisLookupError(str(e)) from e

    def lookup_asn(self, asn: int, original_query: str = "") -> WhoisResponse:
        self._validate_asn(asn)
        query_str = original_query or str(asn)
        try:
            raw = self._provider.lookup_asn(asn)
            return parse_asn_response(raw, query_str)
        except RDAPProviderError as e:
            raise WhoisLookupError(str(e)) from e

    async def _get_cached_record(
        self, session: AsyncSession, query_value: str
    ) -> WhoisRecord | None:
        result = await session.execute(
            select(WhoisRecord).where(WhoisRecord.query_value == query_value)
        )
        return result.scalar_one_or_none()

    def _is_cache_fresh(self, record: WhoisRecord) -> bool:
        if not record.queried_at:
            return False
        age = datetime.now(UTC).replace(tzinfo=None) - record.queried_at
        return age < timedelta(days=self.cache_ttl_days)

    async def _store_record(
        self,
        session: AsyncSession,
        response: WhoisResponse,
        target_id: uuid.UUID | None,
        query_value: str,
    ) -> WhoisRecord:
        """Store or update a WHOIS record in the database."""
        # check if record already exists for this query
        existing = await self._get_cached_record(session, query_value)

        db_fields = response.to_db_fields()
        now = datetime.now(UTC).replace(tzinfo=None)

        if existing:
            for key, value in db_fields.items():
                setattr(existing, key, value)
            existing.queried_at = now
            existing.updated_at = now
            if target_id and not existing.target_id:
                existing.target_id = target_id
            await session.commit()
            return existing
        # create new record
        record = WhoisRecord(
            **db_fields,
            target_id=target_id,
            queried_at=now,
        )
        session.add(record)
        await session.commit()
        return record

    async def link_to_target(
        self, session: AsyncSession, query_value: str, target_id: uuid.UUID
    ) -> WhoisRecord | None:
        """Link an existing WHOIS record to a target.

        Useful when a toolbox lookup was done before the target was added.
        """
        record = await self._get_cached_record(session, query_value)
        if record and not record.target_id:
            record.target_id = target_id
            record.updated_at = datetime.now(UTC).replace(tzinfo=None)
            await session.commit()
        return record

    def _reconstruct_response(self, record: WhoisRecord) -> WhoisResponse:
        data = record.parsed_data
        if not data:
            msg = f"No parsed data stored for record {record.id}"
            raise WhoisLookupError(msg)

        match record.lookup_type:
            case WhoisLookupType.DOMAIN.value:
                return WhoisDomainResponse.model_validate(data)
            case WhoisLookupType.IP.value:
                return WhoisIPResponse.model_validate(data)
            case WhoisLookupType.ASN.value:
                return WhoisASNResponse.model_validate(data)
            case _:
                msg = f"Unknown lookup type: {record.lookup_type}"
                raise WhoisLookupError(msg)

    async def find_by_registrant(
        self, session: AsyncSession, registrant_name: str
    ) -> list[WhoisRecord]:
        """Find all WHOIS records with the same registrant name."""
        result = await session.execute(
            select(WhoisRecord)
            .where(WhoisRecord.registrant_name == registrant_name)
            .where(WhoisRecord.registrant_name != "")
        )
        return list(result.scalars().all())

    async def find_by_registrar(
        self, session: AsyncSession, registrar_name: str
    ) -> list[WhoisRecord]:
        """Find all WHOIS records with the same registrar."""
        result = await session.execute(
            select(WhoisRecord)
            .where(WhoisRecord.registrar_name == registrar_name)
            .where(WhoisRecord.registrar_name != "")
        )
        return list(result.scalars().all())

    async def find_by_network(
        self, session: AsyncSession, network_cidr: str
    ) -> list[WhoisRecord]:
        """Find all WHOIS records in the same network block in ip."""
        result = await session.execute(
            select(WhoisRecord)
            .where(WhoisRecord.network_cidr == network_cidr)
            .where(WhoisRecord.network_cidr != "")
        )
        return list(result.scalars().all())

    async def find_by_country(
        self, session: AsyncSession, country: str
    ) -> list[WhoisRecord]:
        """Find all WHOIS records for a specific country."""
        result = await session.execute(
            select(WhoisRecord)
            .where(WhoisRecord.country == country.upper())
            .where(WhoisRecord.country != "")
        )
        return list(result.scalars().all())

    async def find_by_nameserver(
        self, session: AsyncSession, nameserver: str
    ) -> list[WhoisRecord]:
        """Find all domain records sharing a specific nameserver.

        Uses JSON contains query on the nameservers array.
        """
        result = await session.execute(
            select(WhoisRecord).where(
                WhoisRecord.nameservers.op("@>")(f'["{nameserver}"]')
            )
        )
        return list(result.scalars().all())

    async def get_correlations_for_target(
        self, session: AsyncSession, target_id: uuid.UUID
    ) -> dict[str, list[WhoisRecord]]:
        """Get all correlation groups for a specific target's WHOIS record.

        this is the main method the api/ui calls to show Related Targets.
        """
        result = await session.execute(
            select(WhoisRecord).where(WhoisRecord.target_id == target_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            return {}

        correlations: dict[str, list[WhoisRecord]] = {}

        # same registrant
        if record.registrant_name:
            related = await self.find_by_registrant(session, record.registrant_name)
            others = [r for r in related if r.id != record.id]
            if others:
                correlations["registrant_name"] = others

        # same registrar
        if record.registrar_name:
            related = await self.find_by_registrar(session, record.registrar_name)
            others = [r for r in related if r.id != record.id]
            if others:
                correlations["registrar_name"] = others

        # same network block (IP targets)
        if record.network_cidr:
            related = await self.find_by_network(session, record.network_cidr)
            others = [r for r in related if r.id != record.id]
            if others:
                correlations["network_cidr"] = others

        # same country (IP targets)
        if record.country:
            related = await self.find_by_country(session, record.country)
            others = [r for r in related if r.id != record.id]
            if others:
                correlations["country"] = others

        # shared nameservers (domain targets)
        if record.nameservers:
            ns_related: list[WhoisRecord] = []
            seen_ids = {record.id}
            for ns in record.nameservers:
                matches = await self.find_by_nameserver(session, ns)
                for m in matches:
                    if m.id not in seen_ids:
                        ns_related.append(m)
                        seen_ids.add(m.id)
            if ns_related:
                correlations["nameserver"] = ns_related

        return correlations

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

    def _do_lookup(self, query: str, target_type: TargetType) -> WhoisResponse:
        """Dispatch to the correct provider method."""
        match target_type:
            case TargetType.DOMAIN:
                return self.lookup_domain(query)
            case TargetType.IP:
                return self.lookup_ip(query)
            case TargetType.IP_RANGE:
                return self.lookup_ip(query)
            case TargetType.ASN:
                asn_number = self._extract_asn_number(query)
                return self.lookup_asn(asn_number, query)
            case TargetType.URL:
                domain = self._extract_domain_from_url(query)
                return self.lookup_domain(domain)
            case _:
                msg = f"Unsupported target type for WHOIS: {target_type}"
                raise WhoisValidationError(msg)

    def _normalize_query(self, query: str, target_type: TargetType) -> str:
        # important to normalise for proper caching key
        match target_type:
            case TargetType.DOMAIN:
                return self._normalize_domain(query)
            case TargetType.URL:
                return self._normalize_domain(self._extract_domain_from_url(query))
            case TargetType.ASN:
                # normalize to just digits
                return str(self._extract_asn_number(query))
            case _:
                return query.strip()

    def _detect_type(self, query: str) -> TargetType:
        """Detect the target type from a query string."""
        target_type = validate_target(query)
        if not target_type:
            msg = f"Cannot determine WHOIS lookup type for: {query}"
            raise WhoisValidationError(msg)
        return target_type

    # ----------------------------------------------------------------
    # Validation helpers
    # ----------------------------------------------------------------

    def _normalize_domain(self, domain: str) -> str:
        """Normalize a domain name."""
        domain = domain.strip().lower()
        domain = re.sub(r"^https?://", "", domain)
        domain = domain.split("/")[0].split("?")[0].split("#")[0].split(":")[0]
        return domain.rstrip(".")

    def _extract_asn_number(self, query: str) -> int:
        """Extract the numeric ASN from a query like 'AS13335' or '13335'."""
        cleaned = re.sub(r"^[Aa][Ss]", "", query.strip())
        try:
            return int(cleaned)
        except ValueError as e:
            msg = f"Cannot extract ASN number from: {query}"
            raise WhoisValidationError(msg) from e

    def _extract_domain_from_url(self, url: str) -> str:
        """Extract the domain from a URL."""
        return self._normalize_domain(url)
