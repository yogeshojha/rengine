from __future__ import annotations

import uuid

import pytest
from sqlalchemy import literal, select

from app.api.v1.whois import _target_correlations
from shared.enums.whois import WhoisLookupType
from shared.models.target import Target
from shared.models.whois import WhoisNameserver, WhoisRecord, WhoisRecordSummary
from shared.utils.datetime import utc_now
from shared.utils.infra import is_shared_nameserver
from shared.utils.privacy import registrant_key, registrant_key_sql
from tools.whois.service import WhoisService

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


@pytest.mark.parametrize(
    ("name", "redacted"),
    [("Domains By Proxy, LLC", True), ("Shopify Inc.", False), ("", False)],
)
def test_a_summary_states_whether_its_registrant_is_redacted(name, redacted):
    summary = WhoisRecordSummary(
        id=uuid.uuid4(),
        query_value="example.com",
        lookup_type="domain",
        name="example.com",
        registrant_name=name,
        registrar_name="",
        country="",
        network_cidr="",
        registration_date=None,
        expiration_date=None,
        queried_at=utc_now(),
    )
    assert summary.model_dump()["registrant_redacted"] is redacted


async def _record(
    estate, value: str, *, registrant: str = "", nameservers=()
) -> WhoisRecord:
    record = WhoisRecord(
        query_value=value,
        lookup_type=WhoisLookupType.DOMAIN,
        registrant_name=registrant,
        nameservers=list(nameservers),
    )
    estate.session.add(record)
    await estate.session.flush()
    for ns in nameservers:
        estate.session.add(WhoisNameserver(whois_record_id=record.id, nameserver=ns))
    await estate.session.flush()
    return record


async def _link(estate, value: str, record: WhoisRecord) -> Target:
    target = await estate.session.get(Target, await estate.target(value))
    target.whois_record_id = record.id
    await estate.session.flush()
    return target


async def test_a_record_with_no_target_in_the_project_is_not_a_correlation(estate):
    tag = uuid.uuid4().hex[:8]
    owner = f"Org {tag} Holdings"
    mine = await _record(estate, f"a-{tag}.com", registrant=owner)
    sibling = await _record(estate, f"b-{tag}.com", registrant=owner)
    await _record(estate, f"c-{tag}.com", registrant=owner)
    target = await _link(estate, f"a-{tag}.com", mine)
    await _link(estate, f"b-{tag}.com", sibling)

    groups = await _target_correlations(estate.session, WhoisService(), target)

    assert [(g.correlation_type, g.count) for g in groups] == [("registrant_name", 1)]
    assert [r.id for r in groups[0].records] == [sibling.id]


async def test_a_lone_standalone_record_yields_no_group(estate):
    tag = uuid.uuid4().hex[:8]
    owner = f"Org {tag} Holdings"
    mine = await _record(estate, f"a-{tag}.com", registrant=owner)
    await _record(estate, f"c-{tag}.com", registrant=owner)
    target = await _link(estate, f"a-{tag}.com", mine)

    assert await _target_correlations(estate.session, WhoisService(), target) == []


async def test_a_provider_nameserver_is_not_named_as_the_reason(estate):
    tag = uuid.uuid4().hex[:8]
    own_ns = f"ns1.{tag}.com"
    shared = ("ns1.markmonitor.com", own_ns)
    mine = await _record(estate, f"a-{tag}.com", nameservers=shared)
    sibling = await _record(estate, f"b-{tag}.com", nameservers=shared)
    target = await _link(estate, f"a-{tag}.com", mine)
    await _link(estate, f"b-{tag}.com", sibling)

    groups = await _target_correlations(estate.session, WhoisService(), target)

    assert [(g.correlation_type, g.correlation_value) for g in groups] == [
        ("nameserver", own_ns)
    ]
