from __future__ import annotations

import pytest
from sqlalchemy import literal, select

from shared.utils.infra import is_shared_nameserver
from shared.utils.privacy import registrant_key, registrant_key_sql

pytestmark = pytest.mark.api

NAMES = [
    "Shopify Inc.",
    "Domains By Proxy, LLC",
    "Redacted for Privacy",
    "Shopify, Inc",
    "SHOPIFY INC",
    "Uber Technologies, Inc.",
    "Bugcrowd Inc",
    "Gandi SAS",
    "Foo Holdings Ltd",
    "Acme",
    "Acme Co.",
    "  Spaced   Name  Corp ",
    "REDACTED FOR PRIVACY",
    "",
]


@pytest.mark.parametrize("name", NAMES)
async def test_the_sql_key_and_the_python_key_agree(session, name):
    row = await session.scalar(select(registrant_key_sql(literal(name))))
    assert row == registrant_key(name)


def test_one_registrant_spelled_three_ways_is_one_party():
    spellings = ["Shopify Inc.", "Shopify, Inc", "SHOPIFY INC"]
    assert len({registrant_key(n) for n in spellings}) == 1


def test_a_redacted_registrant_is_nobody():
    assert registrant_key("REDACTED FOR PRIVACY") == ""
    assert registrant_key("Domains By Proxy, LLC") == ""


def test_a_managed_nameserver_is_the_provider():
    assert is_shared_nameserver("gold.foundationdns.com")
    assert is_shared_nameserver("ns1.markmonitor.com")
    assert not is_shared_nameserver("a.ns.hackerone.com")
