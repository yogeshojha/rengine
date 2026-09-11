"""Origin exposure written down, so triage and alerting reach it."""

from __future__ import annotations

import pytest

from shared.definitions.vulnerabilities import Scanner, Severity
from shared.models.scan_correlation import OriginEvidence, OriginFinding, OriginSample
from stages.origin_probe.finding import origin_finding

pytestmark = pytest.mark.pipeline


def _found(kind="origin", confidence="high", evidence=2) -> OriginFinding:
    return OriginFinding(
        kind=kind,
        confidence=confidence,
        exposed=OriginSample(
            host="203.0.113.9", url="https://203.0.113.9", ip="203.0.113.9"
        ),
        fronted=[OriginSample(host="www.example.com", url="https://www.example.com")],
        fronted_total=1,
        evidence=[
            OriginEvidence(kind="content_hash", label="Response body", value="abc"),
            OriginEvidence(kind="favicon_hash", label="Favicon", value="def"),
        ][:evidence],
    )


def test_it_is_rengines_own_finding():
    found = origin_finding(_found())
    assert found.scanner == Scanner.RENGINE.value
    assert found.template_id == "rengine-origin-exposed"


def test_confidence_sets_the_severity():
    assert origin_finding(_found(confidence="high")).severity == Severity.MEDIUM.value
    assert origin_finding(_found(confidence="medium")).severity == Severity.LOW.value


def test_it_names_both_sides_and_the_evidence():
    found = origin_finding(_found())
    assert "203.0.113.9" in found.description
    assert "www.example.com" in found.description
    assert "Response body matches" in found.description
    assert "Favicon matches" in found.description


def test_the_default_vhost_case_reads_differently():
    found = origin_finding(_found(kind="vhost"))
    assert found.template_id == "rengine-default-vhost"
    assert "serves a different site" in found.description


def test_the_fingerprint_is_stable_and_specific():
    """Triage keys on it, so the same pair next week is the same finding."""
    a = origin_finding(_found())
    b = origin_finding(_found())
    assert a.fingerprint == b.fingerprint

    other = _found()
    other.exposed.host = "203.0.113.10"
    assert origin_finding(other).fingerprint != a.fingerprint


def test_an_unknown_kind_still_produces_a_finding():
    found = origin_finding(_found(kind="something-new"))
    assert found.template_id == "rengine-origin-exposed"


def test_it_says_so_when_no_identity_was_recorded():
    found = origin_finding(_found(evidence=0))
    assert "no shared identity recorded" in found.description
