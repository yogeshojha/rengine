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
        "Run digest, failed runs, exposures and exploit intelligence changes",
    ),
    ChannelEvent(
        NotificationType.VULNERABILITY.value,
        "New vulnerabilities",
        "New findings and inferred software CVEs",
    ),
    ChannelEvent(
        NotificationType.INTEGRATION.value,
        "Program changes",
        "Scope and status changes on bug bounty programs",
        CAP_BOUNTY_PROGRAMS,
    ),
    ChannelEvent(
        NotificationType.WATCH.value,
        "Program watches",
        "New in-scope assets on a watched program",
        CAP_PROGRAM_WATCHES,
    ),
    ChannelEvent(
        NotificationType.NEW_CHECKS.value,
        "New checks",
        "Library additions and follow-up run results",
    ),
    ChannelEvent(
        NotificationType.SYSTEM.value,
        "Reports and exports",
        "Ready or failed",
    ),
    ChannelEvent(
        NotificationType.TARGET.value,
        "Enrichment",
        "Failed WHOIS and BGP lookups",
    ),
)

DEFAULT_CHANNEL_EVENTS: tuple[str, ...] = tuple(event.type for event in CHANNEL_EVENTS)


@dataclass(frozen=True)
class ChannelLevel:
    value: str
    label: str


CHANNEL_LEVELS: tuple[ChannelLevel, ...] = (
    ChannelLevel(NotificationSeverity.INFO.value, "All events"),
    ChannelLevel(NotificationSeverity.WARNING.value, "Warning and critical"),
    ChannelLevel(NotificationSeverity.ERROR.value, "Critical only"),
)

DEFAULT_CHANNEL_LEVEL = NotificationSeverity.INFO.value
