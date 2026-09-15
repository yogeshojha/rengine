from __future__ import annotations

import pytest

from stages.dns_posture.config import DnsPostureConfig
from stages.dns_posture.stage import DnsPostureStage
from stages.registry import execution_plan, stage_by_name

pytestmark = pytest.mark.pipeline


def test_the_stage_runs_beside_the_pipeline_and_survives_passive():
    spec = stage_by_name()["dns_posture"]
    assert spec.touches_target is True
    assert spec.passive_capable is True
    assert spec.role == "support"
    assert "subdomain_discovery" in spec.depends_on
    plan = execution_plan()
    step = next(s for s in plan if "dns_posture" in s)
    assert "vulnerability_scan" in step, "nothing waits on it"


def test_selectors_are_cleaned_and_bounded():
    cfg = DnsPostureConfig(dkim_selectors=[" Google ", "google", "", "k1.", "x" * 80])
    assert cfg.dkim_selectors == ["google", "k1"]
    assert DnsPostureConfig().dkim_selectors[:2] == ["default", "google"]


def test_the_stage_applies_to_names_only():
    assert DnsPostureStage.applies_to == frozenset({"domain", "url"})
