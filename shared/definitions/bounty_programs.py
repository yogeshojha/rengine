"""Bug bounty program vocabulary: platforms, scope asset types and what reNgine can scan."""

from __future__ import annotations

import contextlib
import ipaddress
import re
from dataclasses import dataclass
from enum import Enum

import validators

from shared.enums.target import TargetType
from shared.utils.text import strip_control
from shared.utils.validation import normalize_target_value, validate_target


class BountyPlatform(Enum):
    HACKERONE = "hackerone"
    BUGCROWD = "bugcrowd"
    INTIGRITI = "intigriti"
    YESWEHACK = "yeswehack"


class ProgramSource(Enum):
    """Where the row came from. An API row is authoritative over a feed row."""

    API = "api"
    FEED = "feed"


class ProgramState(Enum):
    PUBLIC = "public"
    PRIVATE = "private"


class SubmissionState(Enum):
    OPEN = "open"
    PAUSED = "paused"
    CLOSED = "closed"
    # a feed that does not report it must not be made to guess
    UNKNOWN = "unknown"


class ScopeState(Enum):
    IN_SCOPE = "in_scope"
    OUT_OF_SCOPE = "out_of_scope"


class BountyEvent(Enum):
    PROGRAM_ADDED = "program_added"
    PROGRAM_WENT_PUBLIC = "program_went_public"
    SUBMISSIONS_OPENED = "submissions_opened"
    SUBMISSIONS_CLOSED = "submissions_closed"
    BOUNTIES_STARTED = "bounties_started"
    SCOPE_ADDED = "scope_added"
    SCOPE_REMOVED = "scope_removed"
    WENT_OUT_OF_SCOPE = "went_out_of_scope"
    CAME_INTO_SCOPE = "came_into_scope"


class AssetGroup(Enum):
    NETWORK = "network"
    MOBILE = "mobile"
    CODE = "code"
    OTHER = "other"


@dataclass(frozen=True)
class PlatformSpec:
    key: str
    label: str
    url: str
    supports_private: bool
    note: str
    tag: str
    tag_color: str
    source: str


PLATFORMS: tuple[PlatformSpec, ...] = (
    PlatformSpec(
        key=BountyPlatform.HACKERONE.value,
        label="HackerOne",
        url="https://hackerone.com",
        supports_private=True,
        note="Public and private programs your API token can see",
        tag="hackerone",
        tag_color="#0EA5E9",
        source=ProgramSource.API.value,
    ),
    PlatformSpec(
        key=BountyPlatform.BUGCROWD.value,
        label="Bugcrowd",
        url="https://bugcrowd.com",
        supports_private=False,
        note="Public engagements from the Bounty Targets feed",
        tag="bugcrowd",
        tag_color="#F97316",
        source=ProgramSource.FEED.value,
    ),
    PlatformSpec(
        key=BountyPlatform.INTIGRITI.value,
        label="Intigriti",
        url="https://app.intigriti.com",
        supports_private=False,
        note="Public programs from the Bounty Targets feed",
        tag="intigriti",
        tag_color="#8B5CF6",
        source=ProgramSource.FEED.value,
    ),
    PlatformSpec(
        key=BountyPlatform.YESWEHACK.value,
        label="YesWeHack",
        url="https://yeswehack.com",
        supports_private=False,
        note="Public programs from the Bounty Targets feed",
        tag="yeswehack",
        tag_color="#10B981",
        source=ProgramSource.FEED.value,
    ),
)

SOURCE_LABELS: dict[str, str] = {
    ProgramSource.API.value: "Platform API",
    ProgramSource.FEED.value: "Bounty Targets feed",
}

PLATFORMS_BY_KEY: dict[str, PlatformSpec] = {p.key: p for p in PLATFORMS}


@dataclass(frozen=True)
class AssetTypeSpec:
    key: str
    label: str
    group: AssetGroup
    target_type: TargetType | None
    icon: str
    note: str = ""

    @property
    def targetable(self) -> bool:
        return self.target_type is not None


# every asset type a program can declare; target_type is None for what no scan can reach
ASSET_TYPES: tuple[AssetTypeSpec, ...] = (
    AssetTypeSpec("DOMAIN", "Domain", AssetGroup.NETWORK, TargetType.DOMAIN, "globe"),
    AssetTypeSpec(
        "WILDCARD",
        "Wildcard",
        AssetGroup.NETWORK,
        TargetType.DOMAIN,
        "asterisk",
        "Added as the apex domain",
    ),
    AssetTypeSpec("URL", "URL", AssetGroup.NETWORK, TargetType.URL, "link"),
    AssetTypeSpec(
        "IP_ADDRESS", "IP address", AssetGroup.NETWORK, TargetType.IP, "server"
    ),
    AssetTypeSpec(
        "CIDR", "CIDR range", AssetGroup.NETWORK, TargetType.IP_RANGE, "network"
    ),
    AssetTypeSpec(
        "OTHER",
        "Other",
        AssetGroup.OTHER,
        None,
        "shapes",
        "Free text; ASNs and hostnames are detected and can be added",
    ),
    AssetTypeSpec(
        "APPLE_STORE_APP_ID", "iOS App Store", AssetGroup.MOBILE, None, "smartphone"
    ),
    AssetTypeSpec("TESTFLIGHT", "TestFlight", AssetGroup.MOBILE, None, "smartphone"),
    AssetTypeSpec("OTHER_IPA", "iOS .ipa", AssetGroup.MOBILE, None, "smartphone"),
    AssetTypeSpec(
        "GOOGLE_PLAY_APP_ID", "Google Play", AssetGroup.MOBILE, None, "smartphone"
    ),
    AssetTypeSpec("OTHER_APK", "Android .apk", AssetGroup.MOBILE, None, "smartphone"),
    AssetTypeSpec(
        "WINDOWS_APP_STORE_APP_ID",
        "Microsoft Store",
        AssetGroup.MOBILE,
        None,
        "app-window",
    ),
    AssetTypeSpec("SOURCE_CODE", "Source code", AssetGroup.CODE, None, "file-code"),
    AssetTypeSpec(
        "DOWNLOADABLE_EXECUTABLES", "Executable", AssetGroup.CODE, None, "binary"
    ),
    AssetTypeSpec("AI_MODEL", "AI model", AssetGroup.OTHER, None, "brain"),
    AssetTypeSpec("HARDWARE", "Hardware / IoT", AssetGroup.OTHER, None, "cpu"),
    AssetTypeSpec(
        "SMART_CONTRACT", "Smart contract", AssetGroup.OTHER, None, "file-signature"
    ),
)

ASSET_TYPES_BY_KEY: dict[str, AssetTypeSpec] = {a.key: a for a in ASSET_TYPES}

UNKNOWN_ASSET_TYPE = AssetTypeSpec(
    "UNKNOWN", "Unrecognised", AssetGroup.OTHER, None, "circle-help"
)

# asset types worth running through validate_target; OTHER carries ASNs and hostnames
IMPORTABLE_TYPES: frozenset[str] = frozenset(
    {a.key for a in ASSET_TYPES if a.targetable} | {"OTHER"}
)


@dataclass(frozen=True)
class EventSpec:
    kind: str
    label: str
    description: str
    icon: str
    tone: str
    # a change you can act on now ranks above one that is merely news
    actionable: bool


EVENTS: tuple[EventSpec, ...] = (
    EventSpec(
        BountyEvent.PROGRAM_ADDED.value,
        "New program",
        "A program appeared in your library",
        "sparkles",
        "info",
        actionable=True,
    ),
    EventSpec(
        BountyEvent.SCOPE_ADDED.value,
        "Scope added",
        "The program put a new asset in scope",
        "plus",
        "info",
        actionable=True,
    ),
    EventSpec(
        BountyEvent.CAME_INTO_SCOPE.value,
        "Now in scope",
        "An asset the program excluded is now testable",
        "circle-check",
        "info",
        actionable=True,
    ),
    EventSpec(
        BountyEvent.WENT_OUT_OF_SCOPE.value,
        "Now out of scope",
        "Stop testing this asset",
        "octagon-alert",
        "warning",
        actionable=True,
    ),
    EventSpec(
        BountyEvent.SCOPE_REMOVED.value,
        "Scope removed",
        "The program no longer lists this asset",
        "minus",
        "warning",
        actionable=True,
    ),
    EventSpec(
        BountyEvent.SUBMISSIONS_OPENED.value,
        "Accepting reports",
        "The program reopened for submissions",
        "door-open",
        "info",
        actionable=True,
    ),
    EventSpec(
        BountyEvent.BOUNTIES_STARTED.value,
        "Now pays bounties",
        "The program moved from VDP to paying",
        "banknote",
        "info",
        actionable=True,
    ),
    EventSpec(
        BountyEvent.PROGRAM_WENT_PUBLIC.value,
        "Went public",
        "A private program opened to everyone",
        "globe",
        "muted",
        actionable=False,
    ),
    EventSpec(
        BountyEvent.SUBMISSIONS_CLOSED.value,
        "Stopped accepting",
        "The program paused or closed submissions",
        "door-closed",
        "muted",
        actionable=False,
    ),
)

EVENTS_BY_KIND: dict[str, EventSpec] = {e.kind: e for e in EVENTS}

# the changes worth waking someone for; the rest live in the feed
ALERT_EVENTS: frozenset[str] = frozenset(
    {
        BountyEvent.PROGRAM_ADDED.value,
        BountyEvent.SCOPE_ADDED.value,
        BountyEvent.CAME_INTO_SCOPE.value,
        BountyEvent.WENT_OUT_OF_SCOPE.value,
        BountyEvent.SUBMISSIONS_OPENED.value,
        BountyEvent.BOUNTIES_STARTED.value,
    }
)


# the kinds that may raise an alert; the rest only ever appear in the feed
NOTIFIABLE_EVENTS: tuple[str, ...] = (
    BountyEvent.PROGRAM_ADDED.value,
    BountyEvent.SCOPE_ADDED.value,
    BountyEvent.CAME_INTO_SCOPE.value,
    BountyEvent.WENT_OUT_OF_SCOPE.value,
    BountyEvent.SUBMISSIONS_OPENED.value,
    BountyEvent.BOUNTIES_STARTED.value,
)


class SyncInterval(Enum):
    OFF = "off"
    SIX_HOURS = "six_hours"
    DAILY = "daily"
    WEEKLY = "weekly"


SYNC_INTERVAL_HOURS: dict[str, int] = {
    SyncInterval.SIX_HOURS.value: 6,
    SyncInterval.DAILY.value: 24,
    SyncInterval.WEEKLY.value: 24 * 7,
}

DEFAULT_FEED_INTERVAL = SyncInterval.SIX_HOURS.value

DEFAULT_SYNC_INTERVAL = SyncInterval.DAILY.value
DEFAULT_NOTIFY = True
DEFAULT_NOTIFY_EVENTS: tuple[str, ...] = NOTIFIABLE_EVENTS


def notify_events(settings: dict | None) -> set[str]:
    """Which change kinds may alert, falling back to every notifiable kind."""
    stored = (settings or {}).get("notify_events")
    if not isinstance(stored, list):
        return set(DEFAULT_NOTIFY_EVENTS)
    return {k for k in stored if k in NOTIFIABLE_EVENTS}


def notify_enabled(settings: dict | None) -> bool:
    value = (settings or {}).get("notify")
    return DEFAULT_NOTIFY if value is None else bool(value)


MAX_TAGS_PER_IMPORT = 10
# bounty_events.detail is varchar(500); an instruction is capped far higher
MAX_EVENT_DETAIL = 500

MAX_SEVERITIES: tuple[str, ...] = ("critical", "high", "medium", "low", "none")

_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*://", re.I)
_HOSTNAME_TYPES = frozenset({TargetType.DOMAIN, TargetType.URL})
_IPV6_HOST = re.compile(r"^\[([^\]]+)\]")


def event_spec(kind: str) -> EventSpec:
    return EVENTS_BY_KIND.get(
        kind, EventSpec(kind, kind, "", "circle-help", "muted", actionable=False)
    )


def asset_type_spec(key: str | None) -> AssetTypeSpec:
    return ASSET_TYPES_BY_KEY.get((key or "").upper(), UNKNOWN_ASSET_TYPE)


def scope_state(eligible_for_submission: bool | None) -> ScopeState:
    return ScopeState.IN_SCOPE if eligible_for_submission else ScopeState.OUT_OF_SCOPE


# measured 2026-09-07: the hacker API returns public_mode and soft_launched;
# soft_launched is an invite-only program, so anything but public_mode is private
PUBLIC_STATE = "public_mode"

RAW_STATE_LABELS: dict[str, str] = {
    "public_mode": "Public",
    "soft_launched": "Soft launched",
    "private_mode": "Private",
}


def program_state(raw: str | None) -> ProgramState:
    return ProgramState.PUBLIC if raw == PUBLIC_STATE else ProgramState.PRIVATE


def raw_state_label(raw: str | None) -> str:
    value = (raw or "").strip()
    return RAW_STATE_LABELS.get(
        value, value.replace("_", " ").capitalize() or "Unknown"
    )


def submission_state(raw: str | None) -> SubmissionState:
    value = (raw or "").lower()
    if value == "open":
        return SubmissionState.OPEN
    if value == "paused":
        return SubmissionState.PAUSED
    return SubmissionState.CLOSED


def normalize_identifier(asset_type: str | None, identifier: str) -> str | None:
    """The scannable value behind a scope entry, or None when there is not one."""
    # Postgres refuses NUL and a scope value is stored, so scrub at the source
    value = strip_control(identifier or "").strip()
    if not value:
        return None
    spec = asset_type_spec(asset_type)
    if spec.key not in IMPORTABLE_TYPES:
        return None

    # a scope list writes https://*.example.com for a wildcard
    stripped = _SCHEME.sub("", value).strip()
    host = stripped.split("/")[0]
    if host.startswith("*."):
        # platforms file wildcards under whatever type they like, so the value
        # decides this, not the declared type
        value = host
    elif spec.key == "URL":
        pass
    elif spec.key == "CIDR":
        # a CIDR's slash is its prefix length, never a path
        value = stripped
    else:
        value = host
    value = normalize_target_value(value)
    # a residual wildcard (*.example.*, *-faq.example.com) names no single asset
    return None if not value or "*" in value else value


def _public_host(value: str) -> bool:
    """A program's scope is internet-facing, so a bundle id is not a hostname.

    validators accepts com.etoro.wallet and io.flutter.plugins as domains until
    consider_tld is on. It is deliberately not on in validate_target, because a
    hand-added internal target like traefik.default is legitimate there.
    """
    authority = _SCHEME.sub("", value).split("/")[0].split("?")[0]
    bracketed = _IPV6_HOST.match(authority)
    host = bracketed.group(1) if bracketed else authority.rsplit(":", 1)[0]
    with contextlib.suppress(ValueError):
        ipaddress.ip_address(host)
        return True
    return bool(validators.domain(host, consider_tld=True))


def _canonical(value: str, target_type: TargetType) -> str:
    """The casing reNgine already stores for this target type."""
    if target_type is TargetType.ASN:
        return value.upper()
    if target_type is TargetType.URL:
        return value
    return value.lower()


def target_for_scope(
    asset_type: str | None, identifier: str
) -> tuple[str, TargetType] | None:
    """Normalize a scope entry, then let validate_target decide whether it is a target."""
    value = normalize_identifier(asset_type, identifier)
    if not value:
        return None
    target_type = validate_target(value)
    if not target_type:
        return None
    if target_type in _HOSTNAME_TYPES and not _public_host(value):
        return None
    return _canonical(value, target_type), target_type
