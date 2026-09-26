"""Registries key plugins by name the same strict way and derive their specs from the class."""

from __future__ import annotations

import importlib
from dataclasses import fields
from pathlib import Path

import pytest

import stages.vulnerability_scan.scanners as scanners_package
from reports.base import Section
from reports.registry import SectionSpec, sections
from shared import plugins
from shared.plugins import by_name, classes_in_modules
from stages.base import Stage
from stages.registry import StageSpec, stages
from stages.vulnerability_scan.scanners import SCANNERS, VulnScanner
from stages.vulnerability_scan.scanners.nuclei import NucleiScanner

pytestmark = pytest.mark.pipeline


class _RefusedError(RuntimeError):
    pass


def _plugin(name: str | None) -> type:
    return type(f"Plugin_{name}", (), {"name": name})


def _class_vars(cls: type) -> set[str]:
    return {
        key
        for base in cls.__mro__
        for key, hint in getattr(base, "__annotations__", {}).items()
        if str(hint).startswith("ClassVar")
    }


def test_plugins_are_keyed_by_their_name():
    first, second = _plugin("a"), _plugin("b")
    assert by_name([first, second], kind="x", error=_RefusedError) == {
        "a": first,
        "b": second,
    }


def test_a_plugin_without_a_name_is_refused():
    with pytest.raises(_RefusedError, match="must set a `name`"):
        by_name([_plugin("")], kind="x", error=_RefusedError)


def test_two_plugins_claiming_one_name_are_refused():
    with pytest.raises(_RefusedError, match="Duplicate x name 'a'"):
        by_name([_plugin("a"), _plugin("a")], kind="x", error=_RefusedError)


def test_every_stage_class_attribute_reaches_the_spec():
    assert _class_vars(Stage) <= {f.name for f in fields(StageSpec)}


def test_every_section_class_attribute_but_its_template_reaches_the_spec():
    assert _class_vars(Section) - {"template"} <= {f.name for f in fields(SectionSpec)}


def test_a_stage_spec_carries_its_class_values_frozen():
    for spec in stages():
        cls = spec.stage_cls
        assert spec.depends_on == frozenset(cls.depends_on)
        assert isinstance(spec.depends_on, frozenset)
        assert isinstance(spec.tools, tuple)
        assert spec.transport_tool == cls.transport_tool
        assert spec.config_model is cls.config_model


def test_a_section_spec_carries_its_class_values_frozen():
    for spec in sections().values():
        assert isinstance(spec.requires, frozenset)
        assert spec.order == spec.section_cls.order
        assert spec.defaults == spec.config_model().model_dump()


def test_the_vulnerability_scanners_are_keyed_by_name():
    assert {"nuclei": NucleiScanner} == SCANNERS


def test_a_scanner_module_that_fails_to_import_is_skipped_not_fatal(monkeypatch):
    real = importlib.import_module
    broken = "stages.vulnerability_scan.scanners.nuclei"

    def fake_import(name, *args, **kwargs):
        if name == broken:
            message = "nuclei scanner is broken"
            raise RuntimeError(message)
        return real(name, *args, **kwargs)

    monkeypatch.setattr(plugins.importlib, "import_module", fake_import)
    found = classes_in_modules(
        "stages.vulnerability_scan.scanners",
        Path(scanners_package.__file__).parent,
        VulnScanner,
    )
    assert found == []
