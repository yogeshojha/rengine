from __future__ import annotations

import pytest

from shared.services.asset_query import QuerySyntaxError, parse_query
from shared.services.asset_query.ast import Compare, Term

pytestmark = pytest.mark.api


@pytest.mark.parametrize(
    "query", ["-", '"' * 2000, "\\" * 2000, "%_%" * 600, "\U0001f600", "...", '"---"']
)
def test_a_free_text_word_without_a_letter_or_digit_is_refused(query):
    with pytest.raises(QuerySyntaxError):
        parse_query(query)


@pytest.mark.parametrize("query", ["\U0001f600admin", "a", "/api/v1", "東京", '"x-y"'])
def test_a_free_text_word_with_a_letter_or_digit_parses(query):
    assert isinstance(parse_query(query), Term)


def test_punctuation_inside_a_field_value_parses():
    assert isinstance(parse_query('title:"---"'), Compare)
