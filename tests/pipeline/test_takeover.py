from __future__ import annotations

import pytest

from shared.definitions.domains import TAKEOVER_FINGERPRINTS, takeover_provider
from shared.definitions.vulnerabilities import SCANNER_LABELS, Scanner, Severity
from stages.takeover.stage import TakeoverStage, _finding

pytestmark = pytest.mark.pipeline


@pytest.mark.parametrize(
    ("cname", "provider"),
    [
        ("bucket.s3.amazonaws.com", "AWS S3"),
        ("d123.cloudfront.net", "AWS CloudFront"),
        ("app.azurewebsites.net", "Azure"),
        ("shop.myshopify.com", "Shopify"),
        ("BUCKET.S3.AMAZONAWS.COM.", "AWS S3"),
    ],
)
def test_a_claimable_provider_is_recognised(cname: str, provider: str):
    assert takeover_provider(cname) == provider


@pytest.mark.parametrize(
    "cname", ["edge.example.net", "www.example.com", "", "cdn.cloudflare.net"]
)
def test_anything_else_is_not(cname: str):
    assert takeover_provider(cname) is None


def test_the_fingerprint_is_stable_across_scans():
    a = _finding("a.example.com", "x.s3.amazonaws.com", "AWS S3")
    b = _finding("a.example.com", "x.s3.amazonaws.com", "AWS S3")
    c = _finding("b.example.com", "x.s3.amazonaws.com", "AWS S3")
    d = _finding("a.example.com", "y.s3.amazonaws.com", "AWS S3")

    assert a.fingerprint == b.fingerprint
    assert len({a.fingerprint, c.fingerprint, d.fingerprint}) == 3


def test_the_finding_says_what_it_did_and_did_not_establish():
    found = _finding("a.example.com", "x.s3.amazonaws.com", "AWS S3")

    assert found.scanner == Scanner.RENGINE.value
    assert found.severity == Severity.MEDIUM.value
    assert "AWS S3" in found.remediation
    assert "A released resource can be registered by anyone" in found.description, (
        "an unclaimed name is a condition, not a confirmed takeover"
    )


def test_the_scanner_has_a_label():
    assert SCANNER_LABELS[Scanner.RENGINE.value] == "reNgine"


def test_the_stage_sends_nothing_and_produces_findings():
    assert TakeoverStage.touches_target is False
    assert "vulnerabilities" in TakeoverStage.produces


@pytest.mark.parametrize(
    "cname",
    [
        "bucket.s3-website-us-east-1.amazonaws.com",
        "bucket.s3-website.eu-west-2.amazonaws.com",
    ],
)
def test_a_fingerprint_matches_at_a_label_boundary(cname: str):
    assert takeover_provider(cname) == "AWS S3"


@pytest.mark.parametrize(
    "cname", ["mys3-website.evil.com", "notgithub.io.evil.com", "fakenetlify.app.co"]
)
def test_a_fingerprint_inside_a_label_is_not_a_match(cname: str):
    assert takeover_provider(cname) is None


def test_every_fingerprint_is_matched_whole():
    for suffix, provider in TAKEOVER_FINGERPRINTS:
        assert takeover_provider(f"name.{suffix}") == provider, f"{suffix} ({provider})"
