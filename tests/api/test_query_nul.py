from __future__ import annotations

import pytest

from shared.services.asset_query import QuerySyntaxError, parse_query

pytestmark = pytest.mark.api


@pytest.mark.parametrize("query", ["a\x00b", "host:a\x00b", 'title:"x\x00"'])
def test_a_nul_byte_is_a_parse_error(query):
    with pytest.raises(QuerySyntaxError) as caught:
        parse_query(query)
    assert caught.value.start == query.index("\x00")
