from __future__ import annotations

from datetime import timedelta

import pytest

from shared.models.viewdns import ViewDNSCache
from shared.utils.datetime import utc_now
from tools.viewdns.models import CachedCountQuery, ViewDNSLookupType
from tools.viewdns.service import DEFAULT_CACHE_TTL_DAYS, ViewDNSService

pytestmark = pytest.mark.api

IP = ViewDNSLookupType.REVERSE_IP
NS = ViewDNSLookupType.REVERSE_NS
WHOIS = ViewDNSLookupType.REVERSE_WHOIS


def _row(kind: ViewDNSLookupType, query: str, data: dict, age_days: int = 0):
    return ViewDNSCache(
        lookup_type=kind.value,
        query_value=query,
        response_data=data,
        queried_at=utc_now() - timedelta(days=age_days),
    )


async def test_a_cached_count_is_the_answer_minus_the_target(session):
    session.add_all(
        [
            _row(
                NS,
                "ns1.example.net",
                {
                    "nameserver": "ns1.example.net",
                    "domains": [
                        {"domain": "example.com"},
                        {"domain": "Other.com"},
                        {"domain": ""},
                    ],
                },
            ),
            _row(
                WHOIS,
                "Example Inc",
                {
                    "query": "Example Inc",
                    "matches": [{"domain": "a.com"}, {"domain": "b.com"}],
                },
            ),
            _row(
                IP,
                "192.0.2.1",
                {"host": "192.0.2.1", "domains": [{"name": "x.com"}]},
                age_days=DEFAULT_CACHE_TTL_DAYS + 1,
            ),
        ]
    )
    await session.flush()

    counts = await ViewDNSService(session).cached_counts(
        [
            CachedCountQuery(
                source=NS, query=" NS1.example.net", exclude="EXAMPLE.com"
            ),
            CachedCountQuery(source=WHOIS, query="Example Inc", exclude="example.com"),
            CachedCountQuery(source=WHOIS, query="example inc"),
            CachedCountQuery(source=IP, query="192.0.2.1"),
            CachedCountQuery(source=IP, query="198.51.100.7"),
        ]
    )

    assert [c.count for c in counts] == [1, 2, None, None, None]


async def test_no_queries_reads_nothing(session):
    assert await ViewDNSService(session).cached_counts([]) == []
