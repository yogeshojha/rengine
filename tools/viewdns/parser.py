"""Parsers for ViewDNS.info raw API responses."""

from datetime import date
from typing import Any

from shared.utils.coerce import safe_int
from tools.viewdns.models import (
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
    except ValueError:
        return None


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
        domain_count=safe_int(raw.get("domain_count"), 0),
        domains=domains,
    )


def parse_reverse_ns(raw: dict[str, Any], nameserver: str) -> ReverseNSResponse:
    domains = []
    for d in raw.get("domains") or []:
        domains.append(ReverseNSDomain(domain=d.get("domain", "")))
    return ReverseNSResponse(
        nameserver=nameserver,
        domain_count=safe_int(raw.get("domain_count"), 0),
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
        result_count=safe_int(raw.get("result_count"), 0),
        matches=matches,
    )
