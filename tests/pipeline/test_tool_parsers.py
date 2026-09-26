"""The record parsers that turn raw tool output into what a stage stores."""

from __future__ import annotations

import pytest

from tools.cdncheck.parser import parse_attributions
from tools.naabu.parser import parse_port_record
from tools.wafw00f.parser import parse_detections

pytestmark = pytest.mark.pipeline


def test_naabu_keeps_an_open_port_with_its_defaults():
    assert parse_port_record({"host": "10.0.0.1", "port": 443}) == {
        "ip": "10.0.0.1",
        "port": 443,
        "protocol": "tcp",
        "tls": False,
    }


@pytest.mark.parametrize(
    "rec",
    [
        {"port": 80},
        {"ip": "10.0.0.1"},
        {"ip": "10.0.0.1", "port": "80"},
        {"ip": "10.0.0.1", "port": 0},
        {"ip": "10.0.0.1", "port": 70000},
    ],
)
def test_naabu_drops_a_record_without_an_address_or_a_valid_port(rec: dict):
    assert parse_port_record(rec) is None


def test_cdncheck_names_the_first_kind_that_answered():
    records = [
        {"input": "1.1.1.1", "cdn": True, "cdn_name": "cloudflare", "waf": True},
        {"ip": "2.2.2.2", "waf": True, "waf_name": "akamai"},
        {"input": "3.3.3.3", "cloud": True, "cloud_name": "aws"},
        {"input": "4.4.4.4"},
        {"cdn": True, "cdn_name": "nameless"},
    ]
    assert parse_attributions(records) == {
        "1.1.1.1": {"is_cdn": True, "cdn_name": "cloudflare", "cdn_type": "cdn"},
        "2.2.2.2": {"is_cdn": True, "cdn_name": "akamai", "cdn_type": "waf"},
        "3.3.3.3": {"is_cdn": True, "cdn_name": "aws", "cdn_type": "cloud"},
    }


def test_wafw00f_reads_the_array_through_banner_and_colour_codes():
    raw = (
        "\x1b[1;32m  ~ WAFW00F ~\x1b[0m\n"
        '[{"url": "https://a.example", "detected": true, "firewall": "Cloudflare"},'
        ' {"url": "https://b.example", "detected": true, "firewall": "None"},'
        ' {"url": "https://c.example", "detected": false, "firewall": "Sucuri"},'
        ' {"url": "https://d.example", "detected": true, "firewall": "Generic"}]\n'
    )
    assert parse_detections(raw) == {"https://a.example": "Cloudflare"}


def test_wafw00f_output_without_an_array_names_nothing():
    assert parse_detections("no json here") == {}
