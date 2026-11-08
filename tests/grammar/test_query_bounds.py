from __future__ import annotations

import pytest
from sqlalchemy import column

from app.services.subdomain import SubdomainService
from shared.definitions.asset_query import MAX_QUERY_LENGTH, Op
from shared.models.subdomain import SubdomainFilter
from shared.services.asset_query import parse_query
from shared.services.asset_query.ast import Compare, Not, QuerySyntaxError, Term
from shared.services.asset_query.terms import date_match
from shared.utils.datetime import utc_now

pytestmark = pytest.mark.grammar


def test_a_run_of_negations_folds_without_recursing():
    node = parse_query("-" * (MAX_QUERY_LENGTH - 2) + "x")
    assert isinstance(node, Term)
    assert node.value == "x"


def test_an_odd_run_of_negations_is_one_not():
    node = parse_query("not not not admin")
    assert isinstance(node, Not)
    assert isinstance(node.part, Term)


def test_an_even_run_of_negations_is_the_operand():
    assert isinstance(parse_query("not not admin"), Term)


async def test_status_not_none_keeps_only_answered_hosts(estate, now):
    await estate.scan("example.com", "run", at=now)
    await estate.hosts("run", ["www.example.com"], at=now, status=200)
    await estate.hosts("run", ["dev.example.com"], at=now, status=403)
    await estate.hosts("run", ["dead.example.com"], at=now)
    service = SubdomainService(estate.session)
    scan = estate.scans["run"]

    answered = await service.search(
        estate.project_id, scan, SubdomainFilter(q="status!=none", limit=10)
    )
    assert answered.error is None
    assert answered.total == 2

    not_ok = await service.search(
        estate.project_id, scan, SubdomainFilter(q="status!=200", limit=10)
    )
    assert not_ok.error is None
    assert not_ok.total == 2


@pytest.mark.parametrize(
    ("op", "raw", "future"),
    [
        (Op.GT, "99999999999d", False),
        (Op.MATCH, "9999-12-31", False),
        (Op.LT, "5000y", True),
    ],
)
def test_a_date_past_the_calendar_is_a_query_error(op, raw, future):
    cmp = Compare("discovered", op, (raw,), False, None, 0, len(raw))
    with pytest.raises(QuerySyntaxError, match="out of range"):
        date_match(column("at"), cmp, utc_now(), future=future)
