"""A scan engine can set its own rate and concurrency per tool, and it overrides the preset."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from shared.definitions.intensity import clean_transport_overrides
from shared.services.scan_resolve import merge_engine_context

pytestmark = pytest.mark.pipeline


def _engine(overrides):
    return SimpleNamespace(
        intensity="normal",
        global_headers=[],
        stages={},
        tool_options={},
        transport_overrides=overrides,
    )


def _resolve(overrides):
    return merge_engine_context(_engine(overrides), None, "example.com", "domain")


def test_the_override_sets_the_tool_rate_and_concurrency():
    resolved = _resolve({"nuclei": {"rate": 40, "threads": 50}})
    nuclei = resolved.transports["vulnerability_scan"]
    assert nuclei["rate"] == 40
    assert nuclei["threads"] == 50
    assert resolved.per_tool_rate_limits["nuclei"] == 40


def test_an_untouched_tool_keeps_the_preset():
    resolved = _resolve({"nuclei": {"rate": 40}})
    assert resolved.per_tool_rate_limits["katana"] == 150
    assert resolved.per_tool_rate_limits["httpx"] == 150


def test_no_override_is_the_plain_preset():
    resolved = _resolve({})
    assert resolved.per_tool_rate_limits["nuclei"] == 150


def test_the_validator_clamps_and_rejects():
    assert clean_transport_overrides({"httpx": {"rate": "80"}}) == {
        "httpx": {"rate": 80}
    }
    assert clean_transport_overrides({"httpx": {"rate": None}}) == {}
    with pytest.raises(ValueError, match="not tunable"):
        clean_transport_overrides({"nope": {"rate": 1}})
    with pytest.raises(ValueError, match="not tunable"):
        clean_transport_overrides({"dnsx": {"threads": 5}})
    with pytest.raises(ValueError, match="unknown setting"):
        clean_transport_overrides({"httpx": {"speed": 1}})
