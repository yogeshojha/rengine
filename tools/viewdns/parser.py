"""Parsers for ViewDNS.info raw API responses."""

from datetime import date
from typing import Any

from tools.viewdns.models import (
    IPHistoryRecord,
    IPHistoryResponse,
    ReverseIPDomain,
    ReverseIPResponse,
    ReverseNSDomain,
    ReverseNSResponse,
    ReverseWhoisMatch,
    ReverseWhoisResponse,
)


def _safe_date(value: Any) -> date | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _safe_int(value: Any) -> int:
    if value is None:
        return 0
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def parse_ip_history(raw: dict[str, Any], domain: str) -> IPHistoryResponse:
    records = []
    for r in raw.get("records") or []:
        records.append(
            IPHistoryRecord(
                ip=r.get("ip", ""),
                location=r.get("location", ""),
                owner=r.get("owner", ""),
                last_seen=_safe_date(r.get("lastseen")),
            )
        )
    return IPHistoryResponse(domain=domain, records=records)


def parse_reverse_ip(raw: dict[str, Any], host: str) -> ReverseIPResponse:
    domains = []
    for d in raw.get("domains") or []:
        domains.append(
            ReverseIPDomain(
                name=d.get("name", ""),
                last_resolved=_safe_date(d.get("last_resolved")),
            )
        )
    return ReverseIPResponse(
        host=host,
        domain_count=_safe_int(raw.get("domain_count")),
        domains=domains,
    )


def parse_reverse_ns(raw: dict[str, Any], nameserver: str) -> ReverseNSResponse:
    domains = []
    for d in raw.get("domains") or []:
        domains.append(ReverseNSDomain(domain=d.get("domain", "")))
    return ReverseNSResponse(
        nameserver=nameserver,
        domain_count=_safe_int(raw.get("domain_count")),
        total_pages=_safe_int(raw.get("total_pages")) or 1,
        current_page=_safe_int(raw.get("current_page")) or 1,
        domains=domains,
    )


def parse_reverse_whois(raw: dict[str, Any], query: str) -> ReverseWhoisResponse:
    matches = []
    for m in raw.get("matches") or []:
        matches.append(
            ReverseWhoisMatch(
                domain=m.get("domain", ""),
                created_date=_safe_date(m.get("created_date")),
                registrar=m.get("registrar", ""),
            )
        )
    return ReverseWhoisResponse(
        query=query,
        result_count=_safe_int(raw.get("result_count")),
        total_pages=_safe_int(raw.get("total_pages")) or 1,
        current_page=_safe_int(raw.get("current_page")) or 1,
        matches=matches,
    )
