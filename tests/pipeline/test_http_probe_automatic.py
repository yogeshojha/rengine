"""The HTTP probe runs on every run above passive and carries no switch."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import ClassVar

import pytest

from shared.enums.scan import Intensity, StageRole
from shared.services.scan_resolve import merge_engine_context, validate_overrides
from stages.presets import PRESETS, Preset, preset_stages
from stages.registry import stage_by_name

pytestmark = pytest.mark.pipeline

_PROBE = "http_probe"
_MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "alembic/versions/2026_09_24_http_probe_automatic.py"
)


class _Engine:
    intensity = Intensity.NORMAL.value
    global_headers: ClassVar[list] = []
    stages: ClassVar[dict] = {}
    tool_options: ClassVar[dict] = {}


def _resolve(stages=None, overrides=None, intensity=None):
    engine = _Engine()
    engine.stages = stages or {}
    return merge_engine_context(
        engine, None, "example.com", "domain", overrides=overrides, intensity=intensity
    )


def test_the_probe_is_automatic_support():
    spec = stage_by_name()[_PROBE]
    assert spec.always_on
    assert spec.role == StageRole.SUPPORT.value
    assert spec.touches_target
    assert not spec.passive_capable


def test_a_stored_switch_is_ignored():
    resolved = _resolve(stages={_PROBE: {"enabled": False}})
    assert resolved.stages[_PROBE]["enabled"] is True


def test_a_run_override_is_stripped():
    assert validate_overrides({_PROBE: {"enabled": False}}) == {}
    resolved = _resolve(overrides={_PROBE: {"enabled": False}})
    assert resolved.stages[_PROBE]["enabled"] is True


def test_passive_turns_it_off():
    resolved = _resolve(intensity=Intensity.PASSIVE.value)
    assert resolved.stages[_PROBE]["enabled"] is False


def test_every_port_setting_lives_on_the_port_scan():
    resolved = _resolve(stages={"port_scan": {"http_on_every_port": True}})
    assert resolved.stages["port_scan"]["http_on_every_port"] is True
    assert "probe_all_ports" not in resolved.stages[_PROBE]


def test_no_preset_names_the_probe():
    for preset in PRESETS:
        assert _PROBE not in preset_stages(preset.name)


def test_the_passive_preset_is_passive_intensity():
    passive = next(p for p in PRESETS if p.name == Preset.PASSIVE.value)
    assert passive.intensity == Intensity.PASSIVE.value
    resolved = _resolve(stages=preset_stages(passive.name), intensity=passive.intensity)
    specs = stage_by_name()
    for name, values in resolved.stages.items():
        spec = specs[name]
        if values["enabled"] and spec.touches_target:
            assert spec.passive_capable, name


def _migration():
    spec = importlib.util.spec_from_file_location("http_probe_automatic", _MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("stored", "expected"),
    [
        ({_PROBE: {"enabled": False}}, {}),
        (
            {_PROBE: {"enabled": True, "probe_all_ports": True}},
            {"port_scan": {"http_on_every_port": True}},
        ),
        (
            {_PROBE: {"probe_all_ports": False}, "port_scan": {"profile": "web"}},
            {"port_scan": {"profile": "web"}},
        ),
        ({"port_scan": {"profile": "web"}}, {"port_scan": {"profile": "web"}}),
    ],
)
def test_the_migration_moves_the_setting_and_drops_the_switch(stored, expected):
    migrated, _ = _migration()._migrate(stored)
    assert migrated == expected
