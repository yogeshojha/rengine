from __future__ import annotations

import pytest

from shared.definitions.scan_surface import ROOT_TIERS, Tier
from stages.registry import execution_plan, stage_by_name
from stages.vulnerability_scan.config import VulnerabilityScanConfig

pytestmark = pytest.mark.pipeline


def _before(steps: list[tuple[str, ...]]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    settled: set[str] = set()
    for step in steps:
        for name in step:
            out[name] = set(settled)
        settled |= set(step)
    return out


def test_the_scanner_reads_web_assets_and_ports_not_endpoints():
    spec = stage_by_name()["vulnerability_scan"]

    assert "http_assets" in spec.consumes
    assert "ports" in spec.consumes
    assert "endpoints" not in spec.consumes
    assert "url_discovery" not in spec.depends_on


def test_the_probe_and_the_port_scan_finish_before_the_scanner_runs():
    before = _before(execution_plan())["vulnerability_scan"]

    assert "http_probe" in before
    assert "port_scan" in before
    assert "waf_detect" in before


def test_the_endpoint_switch_is_gone():
    assert "include_endpoints" not in VulnerabilityScanConfig.model_fields
    assert "max_endpoints" not in VulnerabilityScanConfig.model_fields


def test_the_blind_sweep_is_on_by_default_and_a_launch_knob():
    assert VulnerabilityScanConfig().blind_sweep is True
    assert "blind_sweep" in stage_by_name()["vulnerability_scan"].launch_fields


def test_the_blind_tier_runs_last_among_the_root_tiers():
    assert ROOT_TIERS[-1] == Tier.BLIND.value
    assert ROOT_TIERS[0] == Tier.ONE_REQUEST.value
