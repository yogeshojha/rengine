import pytest

from shared.definitions.asset_query import HOST_QUERY
from shared.services.asset_query import parse_query
from shared.services.asset_query.tokens import list_token, token

VALUES = [
    "nginx",
    "a\\b",
    'a\\"b',
    "a\\",
    "C:\\",
    "C:\\Windows\\System32",
    "\\\\srv\\share",
    'say "hi"',
    'a\\" or b',
    "a,b",
    " x ",
    "line\none",
    "a\tb.example",
    "",
]


@pytest.mark.parametrize("value", VALUES)
def test_token_round_trips(value):
    node = parse_query(token("title", ":", value), HOST_QUERY)
    assert node.values == (value,)


@pytest.mark.parametrize("value", [v for v in VALUES if v.strip() == v and v])
def test_list_token_round_trips(value):
    node = parse_query(list_token("title", [value, "z"]), HOST_QUERY)
    assert node.values == (value, "z")


def test_token_matches_the_frontend_spelling():
    assert token("title", ":", "a\\b") == "title:a\\b"
    assert token("title", ":", 'a\\"b') == 'title:"a\\\\\\"b"'
    assert token("title", ":", "C:\\") == 'title:"C:\\\\"'
    assert token("title", ":", "") == 'title:""'
