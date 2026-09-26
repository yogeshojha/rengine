"""Every discovered MCP tool keeps the contract `mcp/ADDING_A_TOOL.md` states."""

from __future__ import annotations

import pytest

from mcp import registry
from mcp.capabilities import Capability
from mcp.tools.base import ToolGroup

pytestmark = pytest.mark.mcp

SPECS = sorted(registry.registry().values(), key=lambda spec: spec.name)


def _undescribed(schema: dict) -> list[str]:
    """Property paths, nested models included, that carry no description."""
    models = {"": schema, **{f"{k}.": v for k, v in schema.get("$defs", {}).items()}}
    return [
        f"{prefix}{name}"
        for prefix, model in models.items()
        for name, prop in model.get("properties", {}).items()
        if not prop.get("description")
    ]


def test_tools_are_discovered():
    assert len(SPECS) > 10


@pytest.mark.parametrize("spec", SPECS, ids=lambda spec: spec.name)
def test_every_input_field_has_a_description(spec):
    assert _undescribed(spec.schema) == []


@pytest.mark.parametrize("spec", SPECS, ids=lambda spec: spec.name)
def test_capability_and_group_are_known(spec):
    assert spec.capability in set(Capability)
    assert spec.group in set(ToolGroup)
    # the registry hands plain strings to the wire and the UI
    assert type(spec.capability) is str
    assert type(spec.group) is str
