from __future__ import annotations

import pytest

from shared.definitions.asset_query import MAX_QUERY_LENGTH
from shared.services.asset_query import parse_query
from shared.services.asset_query.ast import Not, Term

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
