from __future__ import annotations

import pytest
from pydantic import ValidationError

from reports.registry import section, sections


def test_every_section_default_is_one_of_its_options():
    for spec in sections().values():
        spec.config({})


@pytest.mark.parametrize(
    ("name", "raw"),
    [
        ("screenshots", {"columns": "0"}),
        ("compliance", {"frameworks": ["owasp_top10", "unknown"]}),
    ],
)
def test_a_value_outside_the_options_is_refused(name, raw):
    spec = section(name)
    assert spec is not None
    with pytest.raises(ValidationError):
        spec.config(raw)


def test_a_listed_option_is_accepted():
    spec = section("screenshots")
    assert spec is not None
    assert spec.config({"columns": "3"}).columns == "3"
