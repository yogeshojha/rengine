from __future__ import annotations

import re
from pathlib import Path

from mcp import registry as mcp_registry
from shared.definitions.channels import (
    CHANNEL_LABELS,
    CHAT_GROUP_LABELS,
    CHAT_STATE_LABELS,
    RATE_LIMIT_MAX,
    RATE_LIMIT_MIN,
    ChannelKind,
    ChatGroup,
    ChatState,
    CommandSource,
)
from toolbox import registry as toolbox_registry

ROOT = Path(__file__).resolve().parents[2]
MIRROR = Path("/app/frontend-config/channels.ts")
TRANSPORT = ROOT / "channels" / "telegram"


def _enum_values(text: str, name: str) -> set[str]:
    block = re.search(rf"export enum {name} \{{(.*?)\}}", text, re.S)
    assert block, f"{name} is missing from the mirror"
    return set(re.findall(r"= '([^']+)'", block.group(1)))


def test_the_transport_names_no_tool():
    names = set(mcp_registry.registry()) | set(toolbox_registry.registry())
    for path in TRANSPORT.rglob("*.py"):
        source = path.read_text()
        for name in names:
            assert not re.search(rf"[\"']{name}[\"']", source), (
                f"{path.name} names {name}"
            )


def test_the_dispatcher_names_no_tool():
    names = set(mcp_registry.registry()) | set(toolbox_registry.registry())
    source = (ROOT / "channels" / "dispatch.py").read_text()
    for name in names:
        assert not re.search(rf"[\"']{name}[\"']", source), f"dispatch.py names {name}"


def test_the_frontend_mirror_carries_every_value():
    text = MIRROR.read_text()
    assert _enum_values(text, "ChannelKind") == {c.value for c in ChannelKind}
    assert _enum_values(text, "ChatState") == {s.value for s in ChatState}
    assert _enum_values(text, "CommandSource") == {s.value for s in CommandSource}
    assert _enum_values(text, "ChatGroup") == {g.value for g in ChatGroup}


def test_the_frontend_mirror_carries_the_same_labels():
    text = MIRROR.read_text()
    for labels in (
        CHANNEL_LABELS,
        CHAT_STATE_LABELS,
        CHAT_GROUP_LABELS,
    ):
        for label in labels.values():
            assert f"'{label}'" in text, label


def test_the_frontend_mirror_carries_the_rate_bounds():
    text = MIRROR.read_text()
    for name, value in (
        ("RATE_LIMIT_MIN", RATE_LIMIT_MIN),
        ("RATE_LIMIT_MAX", RATE_LIMIT_MAX),
    ):
        assert f"export const {name} = {value:_};" in text, name
