"""DNS recon lookups, standalone or persisted per target."""

import uuid
from collections import Counter

from sqlalchemy.orm import Session

from shared.enums.dns import DnsRecordType
from shared.logging import get_logger
from shared.models.dns import DnsLookup, DnsLookupSummary, DnsRecord
from shared.models.target import Target
from shared.utils.datetime import utc_now
from tools.dnsx.client import DnsxClient, DnsxError
from tools.dnsx.models import DnsxReconResponse
from tools.dnsx.parser import parse_dnsx_jsonl
from tools.runner.models import CommandRecorder

logger = get_logger(__name__)


class DnsxServiceError(Exception):
    """Base exception for DNS service errors."""


class DnsxLookupError(DnsxServiceError):
    """Raised when a DNS lookup fails."""


class DnsxService:
    """DNS lookup service with optional DB persistence."""

    def __init__(
        self,
        timeout: int = 120,
        retry: int = 3,
        threads: int = 10,
        resolvers: list[str] | None = None,
        query_timeout: int | None = None,
        recorder: CommandRecorder | None = None,
        extra_args: list[str] | None = None,
    ) -> None:
        self._timeout = timeout
        self._retry = retry
        self._threads = threads
        self._resolvers = resolvers
        self._query_timeout = query_timeout
        self._recorder = recorder
        self._extra_args = extra_args
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
                    query_timeout=self._query_timeout,
                    recorder=self._recorder,
                    extra_args=self._extra_args,
                )
            except DnsxError as e:
                raise DnsxServiceError(str(e)) from e
        return self._client

    def do_recon(self, domain: str) -> DnsxReconResponse:
        """Run full DNS recon on a single domain (no DB)."""
        result = self.client.recon(domain)

        if not result.success and not result.has_output:
            msg = f"dnsx recon failed for {domain}: {result.error or 'no output'}"
            raise DnsxLookupError(msg)

        parsed = parse_dnsx_jsonl(result.json_records)
        if not parsed:
            msg = f"dnsx returned no parseable results for {domain}"
            raise DnsxLookupError(msg)

        return parsed[0]

    def lookup_and_store(
        self,
        session: Session,
        target_id: uuid.UUID,
        domain: str,
    ) -> DnsLookup:
        """Run DNS recon and store results linked to a target."""
        response = self.do_recon(domain)
        return self.store_results(session, target_id, response)

    def store_results(
        self,
        session: Session,
        target_id: uuid.UUID,
        response: DnsxReconResponse,
    ) -> DnsLookup:
        """Store DNS recon results, replacing any existing DnsLookup for this target."""
        now = utc_now()

        target = session.get(Target, target_id)
        if target and target.dns_lookup_id:
            existing = session.get(DnsLookup, target.dns_lookup_id)
            if existing:
                session.delete(existing)
                session.flush()
            target.dns_lookup_id = None

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
