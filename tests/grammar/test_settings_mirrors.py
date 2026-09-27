from __future__ import annotations

import re
from pathlib import Path

import pytest

from shared.definitions.notification_events import (
    CHANNEL_EVENTS,
    CHANNEL_LEVELS,
    DEFAULT_CHANNEL_LEVEL,
)
from shared.definitions.retention import (
    KEEP_FOREVER,
    SCAN_RETENTION_DAYS,
    SCREENSHOT_RETENTION_DAYS,
)
from shared.enums.notification import NotificationType
from shared.models.notification_channel import DEFAULT_PREFERENCE_TYPES

pytestmark = pytest.mark.grammar

EVENTS = Path("/app/frontend-config/notification-events.ts")
RETENTION = Path("/app/frontend-config/retention.ts")


def _events_mirror() -> list[tuple[str, str, str, str | None]]:
    found = re.findall(
        r"type: '([^']+)',\s*label: '([^']+)',\s*hint: '([^']+)',\s*"
        r"capability: (?:Capability\.(\w+)|null)",
        EVENTS.read_text(),
    )
    return [(t, label, hint, cap.lower() or None) for t, label, hint, cap in found]


def test_channel_events_mirror():
    assert _events_mirror() == [
        (e.type, e.label, e.hint, e.capability) for e in CHANNEL_EVENTS
    ]


def test_channel_levels_mirror():
    text = EVENTS.read_text()
    found = re.findall(r"\{ value: '([^']+)', label: '([^']+)' \}", text)
    assert found == [(level.value, level.label) for level in CHANNEL_LEVELS]
    assert f"DEFAULT_CHANNEL_LEVEL = '{DEFAULT_CHANNEL_LEVEL}'" in text


def test_every_offered_event_is_one_the_product_sends():
    offered = {e.type for e in CHANNEL_EVENTS}
    assert NotificationType.SECURITY.value not in offered
    assert NotificationType.RESOURCE.value not in offered
    assert set(DEFAULT_PREFERENCE_TYPES) == offered


def _days(name: str) -> list[int]:
    block = re.search(
        rf"export const {name}: RetentionOption\[\] = \[(.*?)\];",
        RETENTION.read_text(),
        re.S,
    )
    assert block, f"{name} is missing from the mirror"
    values = re.findall(r"value: (?:'(\d+)'|KEEP_FOREVER)", block.group(1))
    return [int(v) if v else KEEP_FOREVER for v in values]


def test_retention_mirror():
    assert f"KEEP_FOREVER = '{KEEP_FOREVER}'" in RETENTION.read_text()
    assert _days("SCAN_RETENTION") == list(SCAN_RETENTION_DAYS)
    assert _days("SCREENSHOT_RETENTION") == list(SCREENSHOT_RETENTION_DAYS)
