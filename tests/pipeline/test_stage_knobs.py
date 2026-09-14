"""Every engine field is a decision a stage reads; transport comes from intensity."""

from __future__ import annotations

import re
from pathlib import Path
from typing import ClassVar

import pytest

from shared.definitions.intensity import (
    PROFILES,
    RATE_TOOLS,
    TOOL_TIMEOUT,
    Transport,
    transport_for,
)
from shared.enums.scan import Intensity, StageRole
from shared.services.scan_resolve import merge_engine_context
from stages.config import FieldTier
from stages.registry import rate_tools, stages

pytestmark = pytest.mark.pipeline

_ROOT = Path(__file__).resolve().parents[2]
_NO_TRANSPORT = {"waf_detect"}
_TRANSPORT_NAMES = {
    "rate",
    "threads",
    "timeout",
    "retries",
    "dns_threads",
    "dns_timeout",
}
_READ_ELSEWHERE = {
    ("dast_scan", "interactsh"),
    ("url_discovery", "static_extensions"),
    ("url_discovery", "ignored_params"),
    ("url_discovery", "keep_per_family"),
    ("url_discovery", "sibling_cap"),
    ("url_discovery", "drop_noise"),
}


def _package_source(spec) -> str:
    package = Path(spec.stage_cls.__module__.replace(".", "/")).parent
    files = (_ROOT / package).rglob("*.py")
    return "\n".join(p.read_text() for p in files if p.name != "config.py")


def _config_source(spec) -> str:
    return (
        _ROOT / Path(spec.config_model.__module__.replace(".", "/") + ".py")
    ).read_text()


@pytest.mark.parametrize("spec", stages(), ids=lambda s: s.name)
def test_every_field_is_read_by_its_stage(spec):
    body = _package_source(spec)
    own = _config_source(spec)
    for name in spec.config_model.model_fields:
        if name == "enabled" or (spec.name, name) in _READ_ELSEWHERE:
            continue
        declared = len(re.findall(rf"^    {name}:", own, re.M))
        used_in_config = len(re.findall(rf"\b{name}\b", own)) - declared
        used = re.search(rf"\.{name}\b|\"{name}\"", body) or used_in_config > 0
        assert used, f"{spec.name}.{name} is on the form and read by nothing"


@pytest.mark.parametrize("spec", stages(), ids=lambda s: s.name)
def test_no_stage_carries_a_transport_field(spec):
    fields = set(spec.config_model.model_fields)
    assert not (fields & _TRANSPORT_NAMES), (
        f"{spec.name} declares {fields & _TRANSPORT_NAMES}"
    )


@pytest.mark.parametrize("spec", stages(), ids=lambda s: s.name)
def test_every_stage_that_sends_traffic_declares_its_transport(spec):
    if spec.touches_target and spec.tools and spec.name not in _NO_TRANSPORT:
        assert spec.transport_tool is not None, spec.name


@pytest.mark.parametrize("spec", stages(), ids=lambda s: s.name)
def test_tiers_are_declared_once_per_field(spec):
    tiers = spec.config_model.tiers()
    assert set(tiers.values()) <= {FieldTier.BASIC.value, FieldTier.ADVANCED.value}
    assert tiers["enabled"] == FieldTier.BASIC.value


def test_rate_tools_are_the_tools_with_a_rate():
    assert set(rate_tools()) <= set(RATE_TOOLS)
    assert "dnsx" not in rate_tools()


@pytest.mark.parametrize(
    ("tool", "rate", "threads"),
    [
        ("httpx", 150, 150),
        ("naabu", 1000, 100),
        ("nuclei", 150, 25),
        ("katana", 150, 50),
        ("ffuf", 150, 40),
        ("dnsx", None, 30),
        ("banner", None, 32),
    ],
)
def test_normal_keeps_the_numbers_every_stage_shipped_with(tool, rate, threads):
    assert PROFILES[Intensity.NORMAL.value][tool] == (rate, threads)
    assert TOOL_TIMEOUT[tool] >= 1


def test_aggressive_is_louder_than_normal_for_every_rated_tool():
    for tool in RATE_TOOLS:
        normal = PROFILES[Intensity.NORMAL.value][tool]
        loud = PROFILES[Intensity.AGGRESSIVE.value][tool]
        assert loud[0] > normal[0], tool
        assert loud[1] > normal[1], tool


def test_a_weight_scales_the_profile_not_the_ceiling():
    third = transport_for("nuclei", Intensity.NORMAL.value, rate_weight=1 / 3)
    assert third.rate == 50
    capped = transport_for(
        "nuclei", Intensity.AGGRESSIVE.value, rate_weight=1 / 3, ceiling=30
    )
    assert capped.rate == 10


def test_the_context_multipliers_and_ceiling_still_apply():
    t = transport_for(
        "httpx",
        Intensity.NORMAL.value,
        thread_multiplier=2.0,
        timeout_multiplier=3.0,
        rate_override=40,
    )
    assert t == Transport(tool="httpx", rate=40, threads=300, timeout=30, retries=0)


class _Engine:
    intensity = Intensity.NORMAL.value
    global_headers: ClassVar[list] = []
    stages: ClassVar[dict] = {}
    tool_options: ClassVar[dict] = {}


class _Context:
    auth: ClassVar[dict] = {"auth_type": "none"}
    extra_headers: ClassVar[list] = []
    global_rate_limit_override = 20
    per_tool_rate_overrides: ClassVar[dict] = {"naabu": 500}
    thread_multiplier = 1.0
    timeout_multiplier = 1.0
    excluded_subdomains: ClassVar[list] = []
    excluded_paths: ClassVar[list] = []
    excluded_ips: ClassVar[list] = []
    included_subdomains: ClassVar[list] = []
    follow_redirects_override = None
    http_protocol = "both"


def test_the_resolver_hands_every_tool_stage_a_transport():
    resolved = merge_engine_context(_Engine(), _Context(), "example.com", "domain")
    for spec in stages():
        if spec.transport_tool is None:
            assert spec.name not in resolved.transports
            continue
        transport = Transport(**resolved.transports[spec.name])
        assert transport.tool == spec.transport_tool
        if transport.rate is not None:
            assert transport.rate <= 20
    assert resolved.per_tool_rate_limits["naabu"] == 20
    assert resolved.per_tool_rate_limits["httpx"] == 20


def test_aggressive_moves_the_footprint():
    normal = merge_engine_context(_Engine(), None, "example.com", "domain")
    loud = merge_engine_context(
        _Engine(), None, "example.com", "domain", intensity=Intensity.AGGRESSIVE.value
    )
    assert (
        loud.transports["http_probe"]["rate"] > normal.transports["http_probe"]["rate"]
    )
    assert loud.transports["port_scan"]["rate"] > normal.transports["port_scan"]["rate"]


def test_support_stages_are_never_launch_decisions():
    for spec in stages():
        if spec.role == StageRole.SUPPORT.value:
            assert "enabled" in spec.config_model.model_fields
