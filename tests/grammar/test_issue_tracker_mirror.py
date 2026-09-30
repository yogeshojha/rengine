from __future__ import annotations

import re
from pathlib import Path

import pytest

from shared.definitions.issue_trackers import (
    FILING_STATE_LABELS,
    GROUPING_LABELS,
    MAX_FILE_CHECKS,
    MAX_FILE_SELECTION,
    MAX_GROUP_LOCATIONS,
    MAX_LISTED,
    MAX_TRACKERS,
    REMOTE_CATEGORY_LABELS,
    SHEET_REFRESH_SECONDS,
    TRACKERS,
    FilingState,
    Grouping,
    RemoteCategory,
    TrackerKind,
)

pytestmark = pytest.mark.grammar

MIRROR = Path("/app/frontend-config/issue-trackers.ts")


def _enum(text: str, name: str) -> set[str]:
    block = re.search(rf"export enum {name} \{{(.*?)\}}", text, re.S)
    assert block, f"{name} is missing from the mirror"
    return set(re.findall(r"= '([^']+)'", block.group(1)))


def _labels(text: str, name: str) -> list[str]:
    block = re.search(rf"export const {name}[^=]*= \{{(.*?)\n\}};", text, re.S)
    assert block, f"{name} is missing from the mirror"
    return re.findall(r"\]: '([^']+)'", block.group(1))


def _number(text: str, name: str) -> int:
    found = re.search(rf"export const {name} = ([\d_]+);", text)
    assert found, f"{name} is missing from the mirror"
    return int(found.group(1).replace("_", ""))


def test_the_mirror_carries_every_enum_value():
    text = MIRROR.read_text()
    assert _enum(text, "TrackerKind") == {k.value for k in TrackerKind}
    assert _enum(text, "FilingState") == {s.value for s in FilingState}
    assert _enum(text, "RemoteCategory") == {c.value for c in RemoteCategory}
    assert _enum(text, "Grouping") == {g.value for g in Grouping}


def test_the_mirror_carries_every_label_and_limit():
    text = MIRROR.read_text()
    assert _labels(text, "FILING_STATE_LABELS") == list(FILING_STATE_LABELS.values())
    assert _labels(text, "REMOTE_CATEGORY_LABELS") == list(
        REMOTE_CATEGORY_LABELS.values()
    )
    assert _labels(text, "GROUPING_LABELS") == list(GROUPING_LABELS.values())
    assert _number(text, "MAX_TRACKERS") == MAX_TRACKERS
    assert _number(text, "MAX_FILE_SELECTION") == MAX_FILE_SELECTION
    assert _number(text, "MAX_FILE_CHECKS") == MAX_FILE_CHECKS
    assert _number(text, "MAX_GROUP_LOCATIONS") == MAX_GROUP_LOCATIONS
    assert _number(text, "MAX_LISTED") == MAX_LISTED
    assert _number(text, "SHEET_REFRESH_SECONDS") == SHEET_REFRESH_SECONDS


def test_every_tracker_spec_is_mirrored_with_its_fields():
    text = MIRROR.read_text()
    for spec in TRACKERS:
        found = re.search(
            rf"kind: TrackerKind\.{spec.kind.name},\s*label: '([^']+)',"
            rf"\s*urlLabel: '([^']+)'",
            text,
        )
        assert found, f"{spec.kind.value} is missing from the mirror"
        assert found.groups() == (spec.label, spec.url_label)
        for field in spec.fields:
            pattern = rf"field\(\s*'{field.key}',\s*'{re.escape(field.label)}'"
            assert re.search(pattern, text), f"{spec.kind.value}.{field.key} is missing"
