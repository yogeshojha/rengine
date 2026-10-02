from __future__ import annotations

from typing import ClassVar

import pytest

from shared.definitions.default_engine import (
    DEFAULT_ENGINE_INTENSITY,
    DEFAULT_ENGINE_NAME,
    DEFAULT_VULN_SCANNERS,
    VULNERABILITY_STAGE,
    default_engine_stages,
)
from shared.definitions.endpoints import EndpointSource
from shared.services.scan_resolve import merge_engine_context
from stages.registry import stage_by_name
from stages.vulnerability_scan.config import VulnerabilityScanConfig

pytestmark = pytest.mark.pipeline


class _Builtin:
    name = DEFAULT_ENGINE_NAME
    intensity = DEFAULT_ENGINE_INTENSITY
    global_headers: ClassVar[list] = []
    stages: ClassVar[dict] = default_engine_stages()
    tool_options: ClassVar[dict] = {}


_DELTA = {
    VULNERABILITY_STAGE: {"enabled", "scanners"},
}


def test_the_delta_is_the_scanner():
    assert default_engine_stages() == {
        VULNERABILITY_STAGE: {"enabled": True, "scanners": list(DEFAULT_VULN_SCANNERS)},
    }
    assert VulnerabilityScanConfig(
        **default_engine_stages()[VULNERABILITY_STAGE]
    ).enabled


def test_every_other_stage_runs_at_its_default():
    resolved = merge_engine_context(_Builtin(), None, "example.com", "domain")
    for spec in stage_by_name().values():
        if spec.catalog_hidden:
            continue
        expected = spec.defaults
        got = resolved.stage(spec.name)
        for key, value in expected.items():
            if key in _DELTA.get(spec.name, set()):
                continue
            assert got[key] == value, f"{spec.name}.{key}"
    assert resolved.stage("subdomain_discovery")["passive_tools"] == [
        "subfinder",
        "crtname",
    ]
    assert resolved.stage("subdomain_discovery")["zone_transfer"] is False
    assert resolved.stage("subdomain_discovery")["bruteforce"] is False
    assert resolved.stage("port_scan")["enabled"] is False
    assert resolved.stage("url_discovery")["providers"] == [
        EndpointSource.RESPONSE_MINING.value
    ]
    assert resolved.stage(VULNERABILITY_STAGE)["enabled"] is True
    assert resolved.stage(VULNERABILITY_STAGE)["scanners"] == ["nuclei"]
    assert resolved.stage("dast_scan")["enabled"] is False
    assert resolved.intensity == DEFAULT_ENGINE_INTENSITY
