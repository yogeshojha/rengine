from __future__ import annotations

import uuid
from dataclasses import replace

import pytest

from shared.definitions.broken_links import KIND_SEVERITY
from shared.definitions.default_engine import VULNERABILITY_STAGE
from shared.definitions.vulnerabilities import Severity
from shared.enums.scan import AssetKind, StageRole
from shared.services.scan_resolve import ResolvedScanConfig
from stages.base import StageContext
from stages.registry import stages
from stages.takeover.stage import TakeoverStage, _finding

pytestmark = pytest.mark.pipeline

CHECKS = {"takeover", "zone_transfer", "broken_links", "name_ownership", "origin_probe"}


def _stage(vuln: dict) -> TakeoverStage:
    ctx = StageContext(
        scan_id=uuid.uuid4(),
        target_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        target_value="example.com",
        target_type="domain",
        resolved=ResolvedScanConfig(
            target_value="example.com",
            target_type="domain",
            stages={VULNERABILITY_STAGE: vuln},
        ),
    )
    return TakeoverStage(None, ctx)


def _found(severity: str):
    found = _finding("a.example.com", "x.s3.amazonaws.com", "AWS S3")
    return replace(found, severity=severity)


def test_every_support_stage_that_writes_findings_is_a_listed_check():
    writers = {
        s.name
        for s in stages()
        if s.role == StageRole.SUPPORT.value
        and AssetKind.VULNERABILITIES.value in s.produces
    }
    assert writers == CHECKS
    assert {s.name for s in stages() if s.check_of == VULNERABILITY_STAGE} == CHECKS


def test_a_check_declares_every_severity_it_writes():
    by_name = {s.name: s for s in stages()}
    assert set(KIND_SEVERITY.values()) == set(
        by_name["broken_links"].finding_severities
    )
    assert Severity.LOW.value in by_name["origin_probe"].finding_severities


def test_the_vulnerability_scan_severities_filter_the_checks():
    stage = _stage({"enabled": True, "severities": ["critical", "high", "medium"]})
    kept = stage.selected_findings([_found("high"), _found("medium"), _found("low")])
    assert [f.severity for f in kept] == ["high", "medium"]


def test_the_checks_keep_every_severity_when_the_vulnerability_scan_is_off():
    stage = _stage({"enabled": False, "severities": ["critical"]})
    kept = stage.selected_findings([_found("high"), _found("low")])
    assert [f.severity for f in kept] == ["high", "low"]


def test_the_checks_keep_every_severity_when_the_vulnerability_scan_has_no_scanner():
    stage = _stage({"enabled": True, "scanners": [], "severities": ["critical"]})
    kept = stage.selected_findings([_found("high"), _found("low")])
    assert [f.severity for f in kept] == ["high", "low"]
