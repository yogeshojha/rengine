"""The built-in engine resolves and runs subdomain discovery on subfinder alone."""

from __future__ import annotations

from typing import ClassVar

import pytest

from shared.definitions.default_engine import (
    DEFAULT_ENGINE_INTENSITY,
    DEFAULT_ENGINE_NAME,
    DEFAULT_PASSIVE_SOURCES,
    DEFAULT_VULN_SCANNERS,
    SUBDOMAIN_STAGE,
    VULNERABILITY_STAGE,
    default_engine_stages,
)
from shared.services.scan_resolve import merge_engine_context
from stages.registry import stage_by_name
from stages.subdomain.config import SubdomainConfig
from stages.vulnerability_scan.config import VulnerabilityScanConfig

pytestmark = pytest.mark.pipeline


class _Builtin:
    name = DEFAULT_ENGINE_NAME
    intensity = DEFAULT_ENGINE_INTENSITY
    global_headers: ClassVar[list] = []
    stages: ClassVar[dict] = default_engine_stages()
    tool_options: ClassVar[dict] = {}


_DELTA = {
    SUBDOMAIN_STAGE: {"passive_tools"},
    VULNERABILITY_STAGE: {"enabled", "scanners"},
}


def test_the_delta_is_the_sources_and_the_scanner():
    assert default_engine_stages() == {
        SUBDOMAIN_STAGE: {"passive_tools": list(DEFAULT_PASSIVE_SOURCES)},
        VULNERABILITY_STAGE: {"enabled": True, "scanners": list(DEFAULT_VULN_SCANNERS)},
    }
    assert SubdomainConfig(
        **default_engine_stages()[SUBDOMAIN_STAGE]
    ).enabled_sources == ["subfinder"]
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
    assert resolved.stage(SUBDOMAIN_STAGE)["passive_tools"] == ["subfinder"]
    assert resolved.stage(VULNERABILITY_STAGE)["enabled"] is True
    assert resolved.stage(VULNERABILITY_STAGE)["scanners"] == ["nuclei"]
    assert resolved.stage("dast_scan")["enabled"] is False
    assert resolved.intensity == DEFAULT_ENGINE_INTENSITY
