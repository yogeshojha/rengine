from __future__ import annotations

import re
from pathlib import Path

import pytest

from shared.definitions.tripwires import (
    ACTION_LABELS,
    CHECK_STATUS_LABELS,
    FIRE_ON_LABELS,
    FIRE_ON_VERB,
    MAX_NAME,
    MAX_RUNS_PER_DAY,
    RECENT_DAYS,
    SCOPE_LABELS,
    TRIGGER_LABELS,
    ActionKind,
    CheckStatus,
    FireOn,
    OutcomeStatus,
    ScopeKind,
    Trigger,
)

pytestmark = pytest.mark.grammar

MIRROR = Path("/app/frontend-config/tripwires.ts")


def _enum_values(name: str) -> set[str]:
    block = re.search(rf"export enum {name} \{{(.*?)\}}", MIRROR.read_text(), re.S)
    assert block, name
    return set(re.findall(r"= '([a-z_]+)'", block.group(1)))


def _labels(name: str) -> dict[str, str]:
    block = re.search(
        rf"export const {name}[^=]*= \{{(.*?)\n\}};", MIRROR.read_text(), re.S
    )
    assert block, name
    text = MIRROR.read_text()
    out: dict[str, str] = {}
    for enum, key, label in re.findall(r"\[(\w+)\.(\w+)\]: '([^']*)'", block.group(1)):
        member = re.search(rf"export enum {enum} \{{.*?{key} = '([a-z_]+)'", text, re.S)
        assert member, f"{enum}.{key}"
        out[member.group(1)] = label
    return out


def _const(name: str) -> str:
    match = re.search(rf"export const {name} = (.+?);", MIRROR.read_text())
    assert match, name
    return match.group(1).strip("'")


@pytest.mark.parametrize(
    ("ts_name", "members"),
    [
        ("TripwireTrigger", Trigger),
        ("FireOn", FireOn),
        ("ScopeKind", ScopeKind),
        ("ActionKind", ActionKind),
        ("CheckStatus", CheckStatus),
        ("OutcomeStatus", OutcomeStatus),
    ],
)
def test_enum_mirror(ts_name, members):
    assert _enum_values(ts_name) == {m.value for m in members}


@pytest.mark.parametrize(
    ("ts_name", "labels"),
    [
        ("TRIGGER_LABELS", TRIGGER_LABELS),
        ("FIRE_ON_LABELS", FIRE_ON_LABELS),
        ("FIRE_ON_VERB", FIRE_ON_VERB),
        ("SCOPE_LABELS", SCOPE_LABELS),
        ("ACTION_LABELS", ACTION_LABELS),
        ("CHECK_STATUS_LABELS", CHECK_STATUS_LABELS),
    ],
)
def test_label_mirror(ts_name, labels):
    assert _labels(ts_name) == labels


def test_limit_mirror():
    assert int(_const("MAX_NAME")) == MAX_NAME
    assert int(_const("MAX_RUNS_PER_DAY")) == MAX_RUNS_PER_DAY
    assert int(_const("RECENT_DAYS")) == RECENT_DAYS
