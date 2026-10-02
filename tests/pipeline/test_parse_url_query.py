from __future__ import annotations

import pytest

from shared.definitions.endpoints import parse_url

pytestmark = pytest.mark.pipeline


@pytest.mark.parametrize(
    "raw",
    [
        "https://x.com/search?q=a%26b&r=1",
        "https://x.com/p?next=%2Fhome%23frag",
        "https://x.com/p?q=1+2",
        "https://x.com/p?redirect=https%3A%2F%2Fevil.com%2F%3Fa%3D1%26b%3D2",
    ],
)
def test_a_stored_url_parses_back_to_the_same_query(raw: str):
    parsed = parse_url(raw)
    again = parse_url(parsed.url)
    assert again.param_values == parsed.param_values
    assert again.signature == parsed.signature
