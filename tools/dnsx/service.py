"""DNS lookup service - main interface for DNS enrichment.

1. Standalone lookup (no DB) - for pipeline use or ad-hoc queries
2. Persistent lookup (stores in DB, links to target) - post-target-creation enrichment
3. Correlation queries - "which targets share the same NS/MX/A record?"

The stored records enable cross-target intelligence queries:
    - Same nameservers? Same MX? Same IP?
    - CDN detection across targets
    - SOA correlation for related domains
"""

import uuid
from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from shared.enums.dns import DnsRecordType
from shared.logging import get_logger
from shared.models.dns import DnsLookup, DnsLookupSummary, DnsRecord
from shared.models.target import Target
from shared.utils.datetime import utc_now
from tools.dnsx.client import DnsxClient, DnsxError
from tools.dnsx.models import DnsxReconResponse
from tools.dnsx.parser import parse_dnsx_jsonl

logger = get_logger(__name__)


class DnsxServiceError(Exception):
    """Base exception for DNS service errors."""


class DnsxLookupError(DnsxServiceError):
    """Raised when a DNS lookup fails."""


class DnsxService:
    """DNS lookup service with optional DB persistence.

    Used by:
    - Celery tasks (sync, with DB) for post-target enrichment
    - Pipeline stages (sync, with DB) for scan-time DNS resolution
    - Ad-hoc lookups (sync, no DB) for one-off queries for toolbox feature

    Args:
        timeout: Max seconds for dnsx execution.
        retry: Number of DNS retry attempts.
        threads: Concurrent thread count for dnsx.
        resolvers: Optional list of custom DNS resolvers.
    """

    def __init__(
        self,
        timeout: int = 120,
        retry: int = 3,
        threads: int = 10,
        resolvers: list[str] | None = None,
    ) -> None:
        self._timeout = timeout
        self._retry = retry
        self._threads = threads
        self._resolvers = resolvers
        self._client: DnsxClient | None = None

    @property
    def client(self) -> DnsxClient:
        """Lazy-init the dnsx client."""
        if self._client is None:
            try:
                self._client = DnsxClient(
                    timeout=self._timeout,
                    retry=self._retry,
                    threads=self._threads,
                    resolvers=self._resolvers,
                )
            except DnsxError as e:
                raise DnsxServiceError(str(e)) from e
        return self._client

    def do_recon(self, domain: str) -> DnsxReconResponse:
        """Run full DNS recon on a single domain.

        Returns parsed DnsxReconResponse with all record types.
        No DB interaction - pure lookup.

        Args:
            domain: Domain to query (e.g. "example.com").

        Returns:
            DnsxReconResponse with all DNS records.

        Raises:
            DnsxLookupError: If dnsx fails or returns no results.
        """
        result = self.client.recon(domain)

        if not result.success and not result.has_output:
            msg = f"dnsx recon failed for {domain}: {result.error or 'no output'}"
            raise DnsxLookupError(msg)

        parsed = parse_dnsx_jsonl(result.json_records)
        if not parsed:
            msg = f"dnsx returned no parseable results for {domain}"
            raise DnsxLookupError(msg)

        return parsed[0]

    def do_recon_batch(self, domains: list[str]) -> list[DnsxReconResponse]:
        """Run full DNS recon on multiple domains in one dnsx invocation.

        More efficient than calling do_recon per domain since dnsx
        handles concurrency internally.

        Args:
            domains: List of domains to query.

        Returns:
            List of DnsxReconResponse (may be fewer than input if some fail).
        """
        if not domains:
            return []

        result = self.client.recon(domains)

        if not result.success and not result.has_output:
            logger.warning(f"dnsx batch recon failed: {result.error}")
            return []

        return parse_dnsx_jsonl(result.json_records)

    def do_query(
        self,
        domain: str,
        record_types: list[str],
    ) -> DnsxReconResponse:
        """Run targeted DNS query for specific record types.

        Args:
            domain: Domain to query.
            record_types: List of record types (e.g. ["a", "ns", "mx"]).

        Returns:
            DnsxReconResponse (only queried types will be populated).
        """
        result = self.client.query(domain, record_types=record_types)

        if not result.success and not result.has_output:
            msg = f"dnsx query failed for {domain}: {result.error or 'no output'}"
            raise DnsxLookupError(msg)

        parsed = parse_dnsx_jsonl(result.json_records)
        if not parsed:
            msg = f"dnsx returned no parseable results for {domain}"
            raise DnsxLookupError(msg)

        return parsed[0]

    def do_resolve(self, domains: list[str]) -> list[str]:
        """Check which domains resolve (have active DNS).

        Useful as a pipeline pre-filter before deeper scanning.

        Args:
            domains: List of domains to check.

        Returns:
            List of domains that successfully resolved.
        """
        result = self.client.resolve(domains)
        return result.output_lines

    def lookup_and_store(
        self,
        session: Session,
        target_id: uuid.UUID,
        domain: str,
    ) -> DnsLookup:
        """Run DNS recon and store results linked to a target.

        This is the primary method called by the Celery task.

        Args:
            session: SQLAlchemy sync session.
            target_id: Target UUID to link results to.
            domain: Domain to look up.

        Returns:
            DnsLookup record with linked DnsRecord rows.

        Raises:
            DnsxLookupError: If lookup fails.
        """
        response = self.do_recon(domain)
        return self.store_results(session, target_id, response)

    def store_results(
        self,
        session: Session,
        target_id: uuid.UUID,
        response: DnsxReconResponse,
    ) -> DnsLookup:
        """Store DNS recon results in the database.

        Replaces any existing DnsLookup for this target.

        Args:
            session: SQLAlchemy sync session.
            target_id: Target UUID.
            response: Parsed DNS recon response.

        Returns:
            Created/updated DnsLookup record.
        """
        now = utc_now()

        target = session.get(Target, target_id)
        if target and target.dns_lookup_id:
            existing = session.get(DnsLookup, target.dns_lookup_id)
            if existing:
                session.delete(existing)
                session.flush()
            target.dns_lookup_id = None

        # Create parent lookup record
        lookup = DnsLookup(
            host=response.host,
            status_code=response.status_code,
            cdn=response.cdn,
            cdn_name=response.cdn_name,
            parsed_data=response.model_dump(mode="json"),
            queried_at=now,
            created_at=now,
            updated_at=now,
        )
        session.add(lookup)
        session.flush()

        # Create individual record rows
        db_record_dicts = response.to_db_records()
        for rec_dict in db_record_dicts:
            dns_record = DnsRecord(
                dns_lookup_id=lookup.id,
                target_id=target_id,
                record_type=DnsRecordType(rec_dict["record_type"]),
                value=rec_dict.get("value", ""),
                priority=rec_dict.get("priority"),
                weight=rec_dict.get("weight"),
                port=rec_dict.get("port"),
                soa_email=rec_dict.get("soa_email"),
                soa_serial=rec_dict.get("soa_serial"),
                soa_refresh=rec_dict.get("soa_refresh"),
                soa_retry=rec_dict.get("soa_retry"),
                soa_expire=rec_dict.get("soa_expire"),
                soa_minttl=rec_dict.get("soa_minttl"),
                caa_tag=rec_dict.get("caa_tag"),
                caa_flag=rec_dict.get("caa_flag"),
                created_at=now,
            )
            session.add(dns_record)

        session.commit()
        session.refresh(lookup)
        return lookup

    def get_lookup_sync(
        self, session: Session, target_id: uuid.UUID
    ) -> DnsLookup | None:
        """Get existing DNS lookup for a target (sync)."""
        target = session.get(Target, target_id)
        if target and target.dns_lookup_id:
            return session.get(DnsLookup, target.dns_lookup_id)
        return None

    def find_targets_by_record(
        self,
        session: Session,
        record_type: DnsRecordType,
        value: str,
    ) -> list[DnsRecord]:
        """Find all DNS records matching a type and value.

        Example: find_targets_by_record(session, DnsRecordType.NS, "ns1.example.com")

        Returns DnsRecord rows which include target_id for joining.
        """
        result = session.execute(
            select(DnsRecord)
            .where(DnsRecord.record_type == record_type)
            .where(DnsRecord.value == value)
        )
        return list(result.scalars().all())

    def find_targets_sharing_ns(
        self,
        session: Session,
        nameserver: str,
    ) -> list[uuid.UUID]:
        """Find all target IDs that share a given nameserver."""
        result = session.execute(
            select(DnsRecord.target_id)
            .where(DnsRecord.record_type == DnsRecordType.NS)
            .where(DnsRecord.value == nameserver)
            .distinct()
        )
        return list(result.scalars().all())

    def find_targets_sharing_mx(
        self,
        session: Session,
        mx_host: str,
    ) -> list[uuid.UUID]:
        """Find all target IDs that share a given MX host."""
        result = session.execute(
            select(DnsRecord.target_id)
            .where(DnsRecord.record_type == DnsRecordType.MX)
            .where(DnsRecord.value == mx_host)
            .distinct()
        )
        return list(result.scalars().all())

    def find_targets_sharing_ip(
        self,
        session: Session,
        ip: str,
    ) -> list[uuid.UUID]:
        """Find all target IDs that resolve to the same IP."""
        result = session.execute(
            select(DnsRecord.target_id)
            .where(DnsRecord.record_type.in_([DnsRecordType.A, DnsRecordType.AAAA]))
            .where(DnsRecord.value == ip)
            .distinct()
        )
        return list(result.scalars().all())

    def get_record_value_counts(
        self,
        session: Session,
        record_type: DnsRecordType,
    ) -> list[tuple[str, int]]:
        """Get value counts for a record type, ordered by frequency.

        Useful for "top 10 nameservers across all targets" type queries.
        """
        result = session.execute(
            select(DnsRecord.value, func.count(DnsRecord.target_id).label("count"))
            .where(DnsRecord.record_type == record_type)
            .group_by(DnsRecord.value)
            .order_by(func.count(DnsRecord.target_id).desc())
        )
        return list(result.all())

    @staticmethod
    def to_lookup_summary(lookup: DnsLookup) -> DnsLookupSummary:
        """Convert a DnsLookup DB record to a summary for API responses."""
        record_counts: dict[str, int] = {}
        if lookup.records:
            counts = Counter(r.record_type.value for r in lookup.records)
            record_counts = dict(counts)

        return DnsLookupSummary(
            id=lookup.id,
            host=lookup.host,
            status_code=lookup.status_code,
            cdn=lookup.cdn,
            cdn_name=lookup.cdn_name,
            queried_at=lookup.queried_at,
            record_counts=record_counts,
        )
