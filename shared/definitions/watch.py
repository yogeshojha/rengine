"""Program watches: scope-true continuous discovery for a bug bounty program."""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, field
from enum import StrEnum

from shared.definitions.bounty_programs import ScopeState
from shared.enums.scan_schedule import IntervalUnit
from shared.enums.target import TargetType
from shared.services.scope_filter import backtracks_badly, matches_any


class WatchStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"


class WatchHostState(StrEnum):
    NEW = "new"
    UNRESOLVED = "unresolved"
    KNOWN = "known"
    OUT_OF_SCOPE = "out_of_scope"
    PROBING = "probing"
    QUIET = "quiet"
    ALERTED = "alerted"
    MUTED = "muted"


class WatchEventKind(StrEnum):
    WATCH_STARTED = "watch_started"
    WATCH_PAUSED = "watch_paused"
    WATCH_RESUMED = "watch_resumed"
    WATCH_UPDATED = "watch_updated"
    BASELINE_QUEUED = "baseline_queued"
    SCOPE_ADDED = "scope_added"
    SCOPE_REMOVED = "scope_removed"
    HOST_ALERTED = "host_alerted"
    HOST_OUT_OF_SCOPE = "host_out_of_scope"
    STREAM_ERROR = "stream_error"


class WatchCadence(StrEnum):
    OFF = "off"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


CADENCE_INTERVAL: dict[str, tuple[int, str]] = {
    WatchCadence.DAILY.value: (1, IntervalUnit.DAYS.value),
    WatchCadence.WEEKLY.value: (1, IntervalUnit.WEEKS.value),
    WatchCadence.MONTHLY.value: (30, IntervalUnit.DAYS.value),
}

CADENCE_LABELS: dict[str, str] = {
    WatchCadence.OFF.value: "Off",
    WatchCadence.DAILY.value: "Daily",
    WatchCadence.WEEKLY.value: "Weekly",
    WatchCadence.MONTHLY.value: "Monthly",
}

HOST_STATE_LABELS: dict[str, str] = {
    WatchHostState.NEW.value: "Seen",
    WatchHostState.UNRESOLVED.value: "Unresolved",
    WatchHostState.KNOWN.value: "Known",
    WatchHostState.OUT_OF_SCOPE.value: "Out of scope",
    WatchHostState.PROBING.value: "Probing",
    WatchHostState.QUIET.value: "Quiet",
    WatchHostState.ALERTED.value: "Alerted",
    WatchHostState.MUTED.value: "Muted",
}

EVENT_LABELS: dict[str, str] = {
    WatchEventKind.WATCH_STARTED.value: "Watch started",
    WatchEventKind.WATCH_PAUSED.value: "Watch paused",
    WatchEventKind.WATCH_RESUMED.value: "Watch resumed",
    WatchEventKind.WATCH_UPDATED.value: "Settings changed",
    WatchEventKind.BASELINE_QUEUED.value: "Baseline queued",
    WatchEventKind.SCOPE_ADDED.value: "Came into scope",
    WatchEventKind.SCOPE_REMOVED.value: "Left scope",
    WatchEventKind.HOST_ALERTED.value: "New in-scope asset",
    WatchEventKind.HOST_OUT_OF_SCOPE.value: "Out-of-scope certificate",
    WatchEventKind.STREAM_ERROR.value: "Stream error",
}

# the states a hunter reads as "a new host arrived"
FIELD_LABELS: dict[str, str] = {
    "engine_id": "engine",
    "cadence": "repeat",
    "intensity": "intensity",
    "rate_limit": "rate ceiling",
    "probe_on_resolve": "probe on resolve",
    "probe_engine_id": "probe engine",
    "follow_scope": "follow scope changes",
    "alert_unresolved": "alert on unresolved names",
    "alert_query": "alert query",
    "channel_ids": "channels",
    "notify_in_app": "in-app inbox",
}

ARRIVED_STATES: tuple[str, ...] = (
    WatchHostState.PROBING.value,
    WatchHostState.QUIET.value,
    WatchHostState.ALERTED.value,
)

WATCH_RUN_LABEL = "Watching"
PROBE_RUN_LABEL = "Watch probe"
WATCH_TAG = "watch"
CT_SOURCE = "ct_log"
WATCH_HOST_KEY = "_watch_host"

DEFAULT_RATE_LIMIT = 5
MAX_RATE_LIMIT = 1000
MAX_ALERT_QUERY = 2000
MAX_CHANNELS = 20
UNRESOLVED_RETRY_HOURS = 48
RECHECK_BATCH = 200
MAX_NAMES_PER_CERT = 200
MAX_EXCLUSIONS = 1000
MAX_LISTED_ITEMS = 50
MAX_SCOPE_EVENTS = 20
MAX_HOST_NAME = 253
PROBE_STAGES: tuple[str, ...] = ("http_probe", "screenshot")

CT_STATUS_KEY = "watch:ct:status"
CT_STATUS_TTL = 180
CT_POLL_SECONDS = 30
CT_CERT_RETENTION_DAYS = 7


def mark_key(watch_id) -> str:
    return f"watch:{watch_id}"


@dataclass(frozen=True)
class WatchItem:
    """One certspotter watchlist line and the target it belongs to."""

    item: str
    target_value: str
    scope_id: str

    @property
    def subtree(self) -> bool:
        return self.item.startswith(".")

    @property
    def apex(self) -> str:
        return self.item.lstrip(".")

    def matches(self, name: str) -> bool:
        host = name.lower().removeprefix("*.")
        if self.subtree:
            return host == self.apex or host.endswith("." + self.apex)
        return host == self.apex

    def to_dict(self) -> dict:
        return {
            "item": self.item,
            "target_value": self.target_value,
            "scope_id": self.scope_id,
        }

    @classmethod
    def from_dict(cls, raw: dict) -> WatchItem:
        return cls(
            item=str(raw.get("item") or ""),
            target_value=str(raw.get("target_value") or ""),
            scope_id=str(raw.get("scope_id") or ""),
        )


@dataclass
class ScopePlan:
    """What a program's scope turns into once watched."""

    items: list[WatchItem] = field(default_factory=list)
    targets: list[tuple[str, TargetType]] = field(default_factory=list)
    excluded_subdomains: list[str] = field(default_factory=list)
    excluded_ips: list[str] = field(default_factory=list)
    unenforceable: list[str] = field(default_factory=list)

    @property
    def wildcards(self) -> int:
        return sum(1 for i in self.items if i.subtree)


def _wildcard_apex(identifier: str) -> str | None:
    raw = (identifier or "").strip().lower()
    raw = re.sub(r"^[a-z][a-z0-9+.-]*://", "", raw).split("/")[0]
    if raw.startswith("*."):
        apex = raw[2:]
        return apex if apex and "*" not in apex else None
    return None


def host_pattern(identifier: str) -> str | None:
    """An exclusion pattern for an out-of-scope host or wildcard."""
    apex = _wildcard_apex(identifier)
    if apex:
        return f"(^|\\.){re.escape(apex)}$"
    raw = (identifier or "").strip().lower()
    raw = re.sub(r"^[a-z][a-z0-9+.-]*://", "", raw)
    host = raw.split("/")[0].split("?")[0]
    if not host or "*" in host or "/" in raw.rstrip("/"):
        return None
    try:
        ipaddress.ip_address(host)
        return None
    except ValueError:
        pass
    return f"^{re.escape(host)}$"


def excluded_by(name: str, patterns: list[str]) -> bool:
    return matches_any(name.lower(), list(patterns or []))


def plan_scope(scopes) -> ScopePlan:
    """Targets, watch items and exclusions from a program's scope rows."""
    plan = ScopePlan()
    seen_targets: set[str] = set()
    seen_items: set[str] = set()
    for scope in scopes:
        identifier = scope.asset_identifier or ""
        if scope.scope_state == ScopeState.OUT_OF_SCOPE.value:
            entry = (identifier or "").strip()
            if not entry:
                continue
            try:
                ipaddress.ip_network(entry, strict=False)
                if len(plan.excluded_ips) < MAX_EXCLUSIONS:
                    plan.excluded_ips.append(entry)
                else:
                    plan.unenforceable.append(entry)
                continue
            except ValueError:
                pass
            pattern = host_pattern(entry)
            if (
                pattern
                and not backtracks_badly(pattern)
                and len(plan.excluded_subdomains) < MAX_EXCLUSIONS
            ):
                plan.excluded_subdomains.append(pattern)
            else:
                plan.unenforceable.append(entry)
            continue
        if scope.scope_state != ScopeState.IN_SCOPE.value:
            continue
        value = scope.target_value
        kind = scope.target_type
        if isinstance(kind, str):
            kind = TargetType(kind)
        if not value or kind is None:
            continue
        if value not in seen_targets:
            seen_targets.add(value)
            plan.targets.append((value, kind))
        if kind is not TargetType.DOMAIN:
            continue
        item = f".{value}" if _wildcard_apex(identifier) else value
        if item in seen_items:
            continue
        seen_items.add(item)
        plan.items.append(
            WatchItem(item=item, target_value=value, scope_id=str(scope.id))
        )
    return plan
