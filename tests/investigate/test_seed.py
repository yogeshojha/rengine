"""The URL seed a replay builds keeps the finding's port and brackets IPv6."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.investigate.tools import finding_seed
from shared.services.investigate import _seed_url

pytestmark = pytest.mark.investigate


def _vuln(host=None, ip=None, port=None, scheme=None):
    return SimpleNamespace(host=host, ip=ip, port=port, scheme=scheme)


CASES = [
    (
        _vuln(host="app.example.com", port=443, scheme="https"),
        "https://app.example.com:443",
    ),
    (_vuln(host="10.0.0.5", port=80, scheme="http"), "http://10.0.0.5:80"),
    (_vuln(ip="2001:db8::1", port=8443, scheme="https"), "https://[2001:db8::1]:8443"),
    (_vuln(host="api.example.com", scheme="https"), "https://api.example.com"),
    (_vuln(host="svc.example.com", port=8080), "https://svc.example.com:8080"),
]


@pytest.mark.parametrize(("v", "expected"), CASES)
def test_finding_seed(v, expected):
    assert finding_seed(v) == expected


@pytest.mark.parametrize(("v", "expected"), CASES)
def test_rule_seed(v, expected):
    assert _seed_url(v) == expected
