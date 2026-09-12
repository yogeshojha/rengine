from __future__ import annotations

import pytest

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


def test_the_scanner_declares_the_endpoints_it_can_read():
    spec = stage_by_name()["vulnerability_scan"]

    assert "endpoints" in spec.consumes
    assert "url_discovery" in spec.depends_on


def test_the_endpoints_are_discovered_before_the_scanner_runs():
    assert "url_discovery" in _before(execution_plan())["vulnerability_scan"]


def test_site_roots_only_unless_asked():
    assert VulnerabilityScanConfig().include_endpoints is False


def test_the_endpoint_budget_is_an_operator_knob():
    cfg = VulnerabilityScanConfig(include_endpoints=True, max_endpoints=25)

    assert cfg.include_endpoints is True
    assert cfg.max_endpoints == 25


def test_the_launch_dialog_offers_the_endpoint_switch():
    assert "include_endpoints" in stage_by_name()["vulnerability_scan"].launch_fields
