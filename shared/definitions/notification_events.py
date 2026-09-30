"""Event types a notification channel subscribes to, and its minimum level."""

from __future__ import annotations

from dataclasses import dataclass

from shared.definitions.mode_features import CAP_BOUNTY_PROGRAMS, CAP_PROGRAM_WATCHES
from shared.enums.notification import NotificationSeverity, NotificationType


@dataclass(frozen=True)
class ChannelEvent:
    type: str
    label: str
    hint: str
    capability: str | None = None


CHANNEL_EVENTS: tuple[ChannelEvent, ...] = (
    ChannelEvent(
        NotificationType.SCAN.value,
        "Scan results",
        "Run summaries, failed runs and exploit intelligence",
    ),
    ChannelEvent(
        NotificationType.VULNERABILITY.value,
        "New findings",
        "Findings and known exploited software CVEs",
    ),
    ChannelEvent(
        NotificationType.INTEGRATION.value,
        "Program changes",
        "Scope changes on followed programs",
        CAP_BOUNTY_PROGRAMS,
    ),
    ChannelEvent(
        NotificationType.WATCH.value,
        "Program watches",
        "New in-scope assets",
        CAP_PROGRAM_WATCHES,
    ),
    ChannelEvent(
        NotificationType.NEW_CHECKS.value,
        "New checks",
        "Findings from checks added to the library",
    ),
    ChannelEvent(
        NotificationType.TRIPWIRE.value,
        "Tripwires",
        "Saved query matches and rescan results",
    ),
    ChannelEvent(
        NotificationType.SYSTEM.value,
        "Report failures",
        "Reports and exports that did not complete",
    ),
)

DEFAULT_CHANNEL_EVENTS: tuple[str, ...] = tuple(event.type for event in CHANNEL_EVENTS)


@dataclass(frozen=True)
class ChannelLevel:
    value: str
    label: str


CHANNEL_LEVELS: tuple[ChannelLevel, ...] = (
    ChannelLevel(NotificationSeverity.INFO.value, "All events"),
    ChannelLevel(NotificationSeverity.WARNING.value, "Warnings and errors"),
    ChannelLevel(NotificationSeverity.ERROR.value, "Errors only"),
)

DEFAULT_CHANNEL_LEVEL = NotificationSeverity.INFO.value
