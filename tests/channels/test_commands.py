"""The chat set is curated at the tool, one word each, and every command is grouped."""

from __future__ import annotations

import pytest

from channels import commands
from channels.commands import BUILTIN, CommandError, _coerce, bind, parse
from mcp import registry as mcp_registry
from mcp.capabilities import Capability
from shared.definitions.channels import (
    CHAT_GROUP_ORDER,
    COMMAND_PRESETS,
    ChatGroup,
    CommandSource,
)
from toolbox import registry as toolbox_registry

pytestmark = pytest.mark.channels

EXPECTED = {
    "targets",
    "target",
    "add",
    "scan",
    "scans",
    "progress",
    "pause",
    "resume",
    "cancel",
    "vulns",
    "changes",
    "whois",
    "dns",
    "ip",
    "cve",
    "http",
    "subs",
    "help",
    "start",
    "project",
    "projects",
    "whoami",
    "unpair",
}


def test_the_chat_set_is_exactly_the_curated_one():
    assert set(commands.catalog()) == EXPECTED


def test_every_command_is_one_short_word():
    for name in commands.catalog():
        assert mcp_registry.COMMAND_RE.match(name), name
        assert "_" not in name
        assert "-" not in name


def test_every_command_names_a_real_tool_or_builtin():
    for spec in commands.catalog().values():
        if spec.builtin:
            assert spec.name in BUILTIN
        elif spec.source == CommandSource.TOOLBOX.value:
            assert spec.tool in toolbox_registry.registry()
        else:
            assert spec.tool in mcp_registry.registry()


def test_every_command_sits_in_one_group():
    seen = {
        name
        for _group, specs in commands.by_group()
        for spec in specs
        for name in [spec.name]
    }
    assert seen == set(commands.catalog())
    assert [g for g, _ in commands.by_group()] == [
        g
        for g in CHAT_GROUP_ORDER
        if g in {s.group for s in commands.catalog().values()}
    ]
    assert commands.get("whois").group == ChatGroup.LOOKUPS.value
    assert commands.get("scan").group == ChatGroup.SCANS.value


def test_a_tool_without_a_command_stays_out_of_chat():
    by_tool = {spec.tool for spec in commands.catalog().values() if spec.tool}
    assert "describe_query_language" not in by_tool
    assert "focused_rescan" not in by_tool
    assert "group_assets" not in by_tool


def test_presets_bind_their_tools():
    catalog = commands.catalog()
    for preset in COMMAND_PRESETS:
        spec = catalog[preset.name]
        assert spec.tool == preset.tool
        assert spec.presets == preset.args
    assert "dimension" not in [a["name"] for a in catalog["vulns"].args()]


def test_a_lookup_that_touches_the_target_needs_launch():
    http = commands.get("http")
    whois = commands.get("whois")
    assert http is not None
    assert whois is not None
    assert http.capability == Capability.LAUNCH.value
    assert whois.capability == Capability.READ.value


def test_names_fold_case_separators_and_the_bot_suffix():
    assert commands.normalise_name("/Scan@rengine_bot") == "scan"
    assert commands.get("/add-target") is None
    assert commands.get("/Add") is commands.get("add")


@pytest.mark.parametrize(
    ("text", "name", "bare", "kwargs"),
    [
        ("/scan example.com", "scan", ["example.com"], {}),
        (
            "/scan example.com intensity=passive",
            "scan",
            ["example.com"],
            {"intensity": "passive"},
        ),
        (
            "/vulns example.com query='is:kev and severity:critical'",
            "vulns",
            ["example.com"],
            {"query": "is:kev and severity:critical"},
        ),
        (
            "/scan example.com scan-engine=deep",
            "scan",
            ["example.com"],
            {"scan_engine": "deep"},
        ),
        ("/add a.com b.com", "add", ["a.com", "b.com"], {}),
        ("/vulns https://a.com/p?q=1", "vulns", ["https://a.com/p?q=1"], {}),
        ("/help", "help", [], {}),
    ],
)
def test_parse(text, name, bare, kwargs):
    parsed = parse(text)
    assert parsed is not None
    assert parsed.name == name
    assert parsed.bare == bare
    assert parsed.kwargs == kwargs


def test_parse_ignores_plain_text():
    assert parse("hello") is None
    assert parse("   ") is None


def test_parse_refuses_an_unbalanced_quote():
    with pytest.raises(CommandError):
        parse("/vulns example.com query='is:live")


def test_bind_fills_the_value_field_and_the_presets():
    spec = commands.get("vulns")
    assert spec is not None
    args = bind(spec, parse("/vulns example.com limit=5"))
    assert args == {"dimension": "vulnerabilities", "target": "example.com", "limit": 5}
    assert bind(commands.get("scans"), parse("/scans")) == {}
    with pytest.raises(CommandError, match="takes no arguments"):
        bind(commands.get("scans"), parse("/scans abc"))


def test_bind_collects_bare_values_into_a_list_field():
    spec = commands.get("add")
    assert spec is not None
    args = bind(spec, parse("/add a.com b.com tags=client-a,prod"))
    assert args["targets"] == ["a.com", "b.com"]
    assert args["tags"] == ["client-a", "prod"]


def test_bind_names_a_missing_required_argument():
    spec = commands.get("scan")
    assert spec is not None
    with pytest.raises(CommandError, match="Missing target"):
        bind(spec, parse("/scan"))


def test_bind_refuses_an_unknown_argument():
    spec = commands.get("scan")
    assert spec is not None
    with pytest.raises(CommandError, match="no argument speed"):
        bind(spec, parse("/scan example.com speed=fast"))


def test_bind_refuses_a_second_bare_value_on_a_string_field():
    spec = commands.get("scan")
    assert spec is not None
    with pytest.raises(CommandError, match="one value"):
        bind(spec, parse("/scan example.com example.org"))


def test_coercion_by_schema_type():
    assert _coerce("limit", {"type": "integer"}, "5") == 5
    assert _coerce("flag", {"type": "boolean"}, "yes") is True
    assert _coerce("flag", {"type": "boolean"}, "off") is False
    assert _coerce("tags", {"type": "array", "items": {"type": "string"}}, "a, b") == [
        "a",
        "b",
    ]
    with pytest.raises(CommandError, match="whole number"):
        _coerce("limit", {"type": "integer"}, "ten")
    with pytest.raises(CommandError, match="true or false"):
        _coerce("flag", {"type": "boolean"}, "maybe")


def test_usage_reads_off_the_schema():
    assert commands.get("scan").usage == "/scan <target> [key=value]"
    assert commands.get("whois").usage == "/whois <query>"
    assert commands.get("scans").usage == "/scans"
