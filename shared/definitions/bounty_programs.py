"""Bug bounty program vocabulary: platforms, scope asset types and what reNgine can scan."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from shared.enums.target import TargetType
from shared.utils.validation import normalize_target_value, validate_target


class BountyPlatform(Enum):
    HACKERONE = "hackerone"


class ProgramState(Enum):
    PUBLIC = "public"
    PRIVATE = "private"


class SubmissionState(Enum):
    OPEN = "open"
    PAUSED = "paused"
    CLOSED = "closed"


class ScopeState(Enum):
    IN_SCOPE = "in_scope"
    OUT_OF_SCOPE = "out_of_scope"


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


PLATFORMS: tuple[PlatformSpec, ...] = (
    PlatformSpec(
        key=BountyPlatform.HACKERONE.value,
        label="HackerOne",
        url="https://hackerone.com",
        supports_private=True,
        note="Public and private programs your API token can see",
        tag="hackerone",
        tag_color="#0EA5E9",
    ),
)

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

MAX_TAGS_PER_IMPORT = 10

MAX_SEVERITIES: tuple[str, ...] = ("critical", "high", "medium", "low", "none")

_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*://", re.I)


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
    value = (identifier or "").strip()
    if not value:
        return None
    spec = asset_type_spec(asset_type)
    if spec.key not in IMPORTABLE_TYPES:
        return None
    if spec.key != "URL":
        # a scope list writes https://*.example.com for a wildcard
        value = _SCHEME.sub("", value).strip()
        # a path only ever qualifies a URL; a CIDR's slash is its prefix
        if spec.key != "CIDR":
            value = value.split("/")[0].strip()
    value = normalize_target_value(value)
    # a residual wildcard (*.example.*) names no single asset
    return None if not value or "*" in value else value


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
    return (_canonical(value, target_type), target_type) if target_type else None
