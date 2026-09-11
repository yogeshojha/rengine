"""The Bounty Targets feed: public program scope for the platforms with no researcher API."""

from __future__ import annotations

import re
from dataclasses import dataclass

from shared.definitions.bounty_programs import BountyPlatform, ScopeState

BASE_URL = "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/main/data"
SOURCE_NAME = "arkadiyt/bounty-targets-data"
SOURCE_URL = "https://github.com/arkadiyt/bounty-targets-data"
SOURCE_LICENSE = "MIT"


@dataclass(frozen=True)
class FeedSpec:
    platform: str
    file: str
    asset_field: str
    types: dict[str | None, str]


FEEDS: tuple[FeedSpec, ...] = (
    FeedSpec(
        platform=BountyPlatform.BUGCROWD.value,
        file="bugcrowd_data.json",
        asset_field="target",
        types={
            "website": "URL",
            "api": "URL",
            "ip_address": "IP_ADDRESS",
            "network": "CIDR",
            "other": "OTHER",
            "iot": "HARDWARE",
            "hardware": "HARDWARE",
            "ios": "APPLE_STORE_APP_ID",
            "android": "GOOGLE_PLAY_APP_ID",
            "source_code": "SOURCE_CODE",
            "smart_contract": "SMART_CONTRACT",
            None: "OTHER",
        },
    ),
    FeedSpec(
        platform=BountyPlatform.INTIGRITI.value,
        file="intigriti_data.json",
        asset_field="endpoint",
        types={
            "url": "URL",
            "wildcard": "WILDCARD",
            "iprange": "CIDR",
            "ip": "IP_ADDRESS",
            "other": "OTHER",
            "device": "HARDWARE",
            "ios": "APPLE_STORE_APP_ID",
            "android": "GOOGLE_PLAY_APP_ID",
            None: "OTHER",
        },
    ),
    FeedSpec(
        platform=BountyPlatform.YESWEHACK.value,
        file="yeswehack_data.json",
        asset_field="target",
        types={
            "web-application": "URL",
            "api": "URL",
            "wildcard": "WILDCARD",
            "ip-address": "IP_ADDRESS",
            "ip-range": "CIDR",
            "application": "OTHER",
            "other": "OTHER",
            "mobile-application": "OTHER",
            "mobile-application-ios": "APPLE_STORE_APP_ID",
            "mobile-application-android": "GOOGLE_PLAY_APP_ID",
            None: "OTHER",
        },
    ),
)

FEEDS_BY_PLATFORM: dict[str, FeedSpec] = {f.platform: f for f in FEEDS}

SCOPE_KEYS: dict[str, str] = {
    "in_scope": ScopeState.IN_SCOPE.value,
    "out_of_scope": ScopeState.OUT_OF_SCOPE.value,
}

_HANDLE_CHARS = re.compile(r"[^a-zA-Z0-9._-]+")


def asset_type(spec: FeedSpec, raw: str | None) -> str:
    return spec.types.get((raw or "").strip().lower() or None, "OTHER")


def handle_for(platform: str, entry: dict) -> str | None:
    """A stable per-platform identity."""
    if platform == BountyPlatform.INTIGRITI.value:
        candidate = entry.get("handle") or entry.get("id")
    elif platform == BountyPlatform.YESWEHACK.value:
        candidate = entry.get("id") or entry.get("slug")
    else:
        url = str(entry.get("url") or "").rstrip("/")
        candidate = url.rsplit("/", 1)[-1] if url else None
    cleaned = _HANDLE_CHARS.sub("-", str(candidate or "")).strip("-")
    return cleaned[:200] or None


def _amount(value) -> float | None:
    if isinstance(value, dict):
        value = value.get("value")
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _currency(*values) -> str | None:
    for value in values:
        if isinstance(value, dict) and value.get("currency"):
            return str(value["currency"])[:16]
    return None


def payout(entry: dict) -> tuple[float | None, float | None, str | None]:
    """Minimum, maximum and currency, where the platform reports them."""
    low = _amount(entry.get("min_bounty"))
    high = _amount(entry.get("max_bounty") or entry.get("max_payout"))
    return low, high, _currency(entry.get("min_bounty"), entry.get("max_bounty"))
