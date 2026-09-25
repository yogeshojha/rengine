from __future__ import annotations

import pytest

from stages.vhost.stage import host_for

pytestmark = pytest.mark.pipeline


@pytest.mark.parametrize(
    ("label", "apex", "expected"),
    [
        ("admin", "example.com", "admin.example.com"),
        ("Admin", "example.com", "admin.example.com"),
        ("STAGING", "Example.COM", "staging.example.com"),
        ("dev.", "example.com", None),
        ("has space", "example.com", None),
    ],
)
def test_a_label_becomes_the_stored_host_name(label, apex, expected):
    assert host_for(label, apex) == expected
