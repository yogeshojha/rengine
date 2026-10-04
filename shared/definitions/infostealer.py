"""Infostealer infections: machines whose saved logins name a target's domain."""

from __future__ import annotations

from datetime import timedelta
from enum import StrEnum

SOURCE_NAME = "Hudson Rock"
SOURCE_URL = "https://www.hudsonrock.com/free-tools"

STALE_AFTER = timedelta(days=7)
REQUEST_TIMEOUT = 30.0
REQUEST_SPACING = 0.25
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
LOOKUP_BATCH = 100

MAX_DOMAIN_LENGTH = 253
MAX_HOST_LENGTH = 500
MAX_PATH_LENGTH = 400
MAX_NAME_LENGTH = 120
MAX_ERROR_LENGTH = 1000
MAX_LOGINS = 400
MAX_FAMILIES = 40
MAX_APPLICATIONS = 40
MAX_THIRD_PARTIES = 60
MAX_PATHS_PER_HOST = 50


class Audience(StrEnum):
    EMPLOYEE = "employee"
    USER = "user"


AUDIENCE_ORDER: tuple[str, ...] = tuple(a.value for a in Audience)

AUDIENCE_LABELS: dict[str, str] = {
    Audience.EMPLOYEE.value: "Employees",
    Audience.USER.value: "Users",
}


class PasswordStrength(StrEnum):
    TOO_WEAK = "too_weak"
    WEAK = "weak"
    MEDIUM = "medium"
    STRONG = "strong"


STRENGTH_ORDER: tuple[str, ...] = tuple(s.value for s in PasswordStrength)

STRENGTH_LABELS: dict[str, str] = {
    PasswordStrength.TOO_WEAK.value: "Too weak",
    PasswordStrength.WEAK.value: "Weak",
    PasswordStrength.MEDIUM.value: "Medium",
    PasswordStrength.STRONG.value: "Strong",
}


class HostStanding(StrEnum):
    WEB_ASSET = "web_asset"
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    ABSENT = "absent"


STANDING_ORDER: tuple[str, ...] = tuple(s.value for s in HostStanding)

STANDING_LABELS: dict[str, str] = {
    HostStanding.WEB_ASSET.value: "Web asset",
    HostStanding.RESOLVED.value: "No web response",
    HostStanding.UNRESOLVED.value: "Not resolved",
    HostStanding.ABSENT.value: "Not in scan",
}

QUERY_FIELD = "infostealer"
CREDENTIALS_FIELD = "infostealer.credentials"
ANY = "any"
NONE = "none"
QUERY_VALUES: tuple[str, ...] = (*AUDIENCE_ORDER, ANY, NONE)

NOT_APPLICABLE_REASON = "Applies to domain and URL targets with a registrable domain."
LOOKUPS_OFF_REASON = "Infostealer lookups are off in Settings."


def any_query() -> str:
    return f"{QUERY_FIELD}:{ANY}"
